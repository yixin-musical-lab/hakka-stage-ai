from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now_isoformat
from app.models import AiTask, PracticeReport, PracticeSubmission
from app.schemas import (
    PracticeIssuePoint,
    PracticeReportContent,
    PracticeReportResponse,
    PracticeSubmissionCreateRequest,
    PracticeSubmissionDetailResponse,
    PracticeSubmissionSummaryResponse,
)


def build_practice_report_title(submission: PracticeSubmission) -> str:
    """根据提交记录生成报告标题，方便列表和导出文件识别。"""

    return f"{submission.student_name} · {submission.task_title}练习观察报告"


def normalized_evaluation_focus(values: list[str]) -> list[str]:
    """清理前端传入的评价重点，避免 JSONB 中保存空字符串。"""

    cleaned = [value.strip() for value in values if value.strip()]
    return cleaned or ["拍摄质量", "节奏", "动作完整度", "动作稳定"]


def create_submission_from_request(request: PracticeSubmissionCreateRequest) -> PracticeSubmission:
    """把创建请求转换成 ORM 对象，集中维护默认值。"""

    return PracticeSubmission(
        course_title=request.course_title,
        task_title=request.task_title,
        task_description=request.task_description,
        student_name=request.student_name,
        student_group=request.student_group,
        video_url=request.video_url,
        video_file_name=request.video_file_name,
        video_duration_seconds=request.video_duration_seconds,
        video_notes=request.video_notes,
        reference_action_name=request.reference_action_name,
        reference_video_url=request.reference_video_url,
        evaluation_focus=normalized_evaluation_focus(request.evaluation_focus),
        status="submitted",
    )


def submission_summary(db: Session, submission: PracticeSubmission) -> PracticeSubmissionSummaryResponse:
    """把 ORM 练习提交记录转成列表摘要，并附带当前报告状态。"""

    report = latest_report_for_submission(db, submission.id)
    return PracticeSubmissionSummaryResponse(
        id=submission.id,
        course_title=submission.course_title,
        task_title=submission.task_title,
        student_name=submission.student_name,
        student_group=submission.student_group,
        status=submission.status,
        report_status=report.status if report else None,
        analysis_mode=report.analysis_mode if report else None,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


def submission_detail(db: Session, submission: PracticeSubmission) -> PracticeSubmissionDetailResponse:
    """组装提交详情和最新练习报告。"""

    report = latest_report_for_submission(db, submission.id)
    return PracticeSubmissionDetailResponse(
        id=submission.id,
        course_title=submission.course_title,
        task_title=submission.task_title,
        task_description=submission.task_description,
        student_name=submission.student_name,
        student_group=submission.student_group,
        video_url=submission.video_url,
        video_file_name=submission.video_file_name,
        video_duration_seconds=submission.video_duration_seconds,
        video_notes=submission.video_notes,
        reference_action_name=submission.reference_action_name,
        reference_video_url=submission.reference_video_url,
        evaluation_focus=submission.evaluation_focus,
        status=submission.status,
        report=report_response(report) if report else None,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


def report_response(report: PracticeReport) -> PracticeReportResponse:
    """把 ORM 报告对象转换成响应模型。"""

    return PracticeReportResponse.model_validate(report, from_attributes=True)


def latest_report_for_submission(db: Session, submission_id: UUID) -> PracticeReport | None:
    """读取某次提交的最新报告。

    当前一条提交只维护一份报告；使用倒序查询是为了后续支持重新分析时仍然兼容。
    """

    return (
        db.query(PracticeReport)
        .filter(PracticeReport.submission_id == submission_id)
        .order_by(PracticeReport.updated_at.desc())
        .first()
    )


def upsert_basic_practice_report(db: Session, submission: PracticeSubmission) -> PracticeReport:
    """创建或刷新基础观察报告。

    这里不执行视频解码、姿态估计或大模型调用，只把已知元数据整理成可复核报告草稿；
    真实 RTMPose / DTW / LLM 链路后续应放到 Worker 或云端 GPU。
    """

    report = latest_report_for_submission(db, submission.id)
    content = build_basic_report_content(submission).model_dump()
    raw_analysis_info = {
        "pipeline": "manual_first_stage",
        "video_file_processing": "not_connected",
        "pose_estimation": "not_connected",
        "dtw_alignment": "not_connected",
        "llm_report": "not_connected",
        "generated_at": utc_now_isoformat(),
    }

    if report is None:
        report = PracticeReport(
            submission_id=submission.id,
            title=build_practice_report_title(submission),
            status="ai_observed",
            analysis_mode=content["observation_mode"],
            content=content,
            raw_analysis_info=raw_analysis_info,
        )
        db.add(report)
    elif report.status != "reviewed":
        report.title = build_practice_report_title(submission)
        report.status = "ai_observed"
        report.analysis_mode = content["observation_mode"]
        report.content = content
        report.raw_analysis_info = raw_analysis_info
        report.updated_at = datetime.utcnow()

    submission.status = "analyzed" if report.status != "reviewed" else "reviewed"
    submission.updated_at = datetime.utcnow()
    db.flush()
    return report


def build_basic_report_content(submission: PracticeSubmission) -> PracticeReportContent:
    """根据提交元数据生成第一阶段基础观察报告。"""

    has_reference = bool(submission.reference_video_url.strip())
    observation_mode = "reference_comparison_pending" if has_reference else "basic_observation"
    focus_text = "、".join(submission.evaluation_focus or [])
    duration_text = _format_duration(submission.video_duration_seconds)

    issue_points = [
        PracticeIssuePoint(
            category="拍摄质量",
            description="系统已收到练习视频地址，第一阶段尚未自动抽帧检查全身入镜、光线和遮挡。",
            suggestion="老师复核时先确认学生是否全身入镜、画面是否稳定、手脚是否频繁出画。",
        ),
        PracticeIssuePoint(
            category="练习重点",
            description=f"本次练习关注：{focus_text}。",
            suggestion="复核时可围绕这些重点补充一到两条学生能马上执行的改进任务。",
        ),
    ]

    if submission.video_duration_seconds is not None and not 15 <= submission.video_duration_seconds <= 60:
        issue_points.append(
            PracticeIssuePoint(
                category="视频时长",
                description=f"视频时长为 {duration_text}，可能不在 15-60 秒的建议范围内。",
                suggestion="下一次打卡建议控制在 15-60 秒，方便老师快速复核和后续 Worker 分析。",
            )
        )

    if has_reference:
        issue_points.append(
            PracticeIssuePoint(
                category="标准动作参考",
                description="本次已记录标准动作参考视频，但后端 API 暂未接入 RTMPose 和 DTW 对齐。",
                suggestion="后续 Worker 接入后，再生成手臂高度、重心、节奏等结构化差异观察。",
            )
        )
        boundary_note = "已记录标准动作参考；当前第一阶段仅生成基础观察稿，不自动判定动作正确率。"
    else:
        issue_points.append(
            PracticeIssuePoint(
                category="标准动作参考",
                description="本次缺少标准动作参考视频，不能进行接近标准动作的对比观察。",
                suggestion="如需后续做动作差异观察，请先补充同一动作的正面全身标准示范视频。",
            )
        )
        boundary_note = "缺少标准动作参考，本次仅提供拍摄质量、练习完整度和老师复核建议，不做专业自动判分。"

    return PracticeReportContent(
        title=build_practice_report_title(submission),
        observation_mode=observation_mode,
        summary="本报告为第一阶段练习辅助观察稿，已整理提交信息、练习重点和老师复核建议。",
        video_basic_info=[
            f"课程 / 片段：{submission.course_title or '未填写'}",
            f"练习任务：{submission.task_title}",
            f"学生：{submission.student_name}{f'（{submission.student_group}）' if submission.student_group else ''}",
            f"视频文件：{submission.video_file_name or '未填写文件名'}",
            f"视频时长：{duration_text}",
        ],
        shooting_quality_feedback=[
            "建议确认画面是否保持全身入镜，尤其是手臂打开和脚步移动时不要出画。",
            "建议确认光线是否稳定、背景是否简单，避免影响后续姿态点提取。",
        ],
        rhythm_and_completion_observations=[
            "第一阶段尚未接入节拍和 DTW 对齐，暂由老师根据视频判断动作是否完整完成。",
            "如果学生动作明显中断，可在老师点评中拆成更短的下一次练习任务。",
        ],
        posture_and_stability_observations=[
            "第一阶段尚未接入人体关键点检测，暂不输出关节角度或重心结论。",
            "老师可优先观察站稳重心、手臂高度、左右打开幅度和转身后定点。",
        ],
        structured_issue_points=issue_points,
        ai_suggestions=[
            "先保证拍摄清晰和全身入镜，再追求动作细节。",
            "学生下一次练习可以只聚焦一个问题，例如节奏稳定或手臂打开高度。",
            "老师复核后再发布最终点评，避免学生把系统草稿当成专业判分。",
        ],
        teacher_review_points=[
            "视频是否符合 15-60 秒、固定机位、全身入镜的打卡要求。",
            "学生是否完成了老师布置的核心动作或节拍段落。",
            "是否需要补拍，或改成更短、更明确的下一次练习任务。",
        ],
        next_practice_tasks=[
            "按老师确认后的重点，重新完成 15-30 秒短片段练习。",
            "录制前先站在画面中央，确认手脚完整入镜。",
        ],
        boundary_note=boundary_note,
    )


def review_practice_report(
    db: Session,
    report: PracticeReport,
    edited_content: PracticeReportContent,
    teacher_feedback: str,
    reviewed_by: str,
) -> PracticeReport:
    """保存老师复核稿，并同步更新提交状态。"""

    now = datetime.utcnow()
    content = edited_content.model_dump()
    if teacher_feedback:
        content["teacher_final_comment"] = teacher_feedback
    report.edited_content = content
    report.teacher_feedback = teacher_feedback or edited_content.teacher_final_comment
    report.reviewed_by = reviewed_by
    report.reviewed_at = now
    report.status = "reviewed"
    report.updated_at = now

    submission = db.get(PracticeSubmission, report.submission_id)
    if submission is not None:
        submission.status = "reviewed"
        submission.updated_at = now

    db.flush()
    return report


def render_practice_report_markdown(report: PracticeReport) -> str | None:
    """把练习辅助观察报告渲染成 Markdown 文本。"""

    content = report.edited_content or report.content
    if not content:
        return None

    return "\n\n".join(
        [
            f"# {content.get('title', report.title)}",
            "## 总体观察\n" + str(content.get("summary", "")),
            "## 视频基本信息\n" + _markdown_list(content.get("video_basic_info", [])),
            "## 拍摄质量反馈\n" + _markdown_list(content.get("shooting_quality_feedback", [])),
            "## 节奏与完整度观察\n" + _markdown_list(content.get("rhythm_and_completion_observations", [])),
            "## 姿态和动作稳定性观察\n" + _markdown_list(content.get("posture_and_stability_observations", [])),
            "## 结构化观察点\n" + _issue_markdown(content.get("structured_issue_points", [])),
            "## 练习建议\n" + _markdown_list(content.get("ai_suggestions", [])),
            "## 老师复核重点\n" + _markdown_list(content.get("teacher_review_points", [])),
            "## 下一次练习任务\n" + _markdown_list(content.get("next_practice_tasks", [])),
            "## 老师最终点评\n" + str(report.teacher_feedback or content.get("teacher_final_comment", "") or "暂无"),
            "## 能力边界\n" + str(content.get("boundary_note", "")),
        ]
    )


def delete_practice_submission_with_related_data(db: Session, submission_id: UUID) -> bool:
    """删除练习提交、关联报告和分析任务。"""

    submission = db.get(PracticeSubmission, submission_id)
    if submission is None:
        return False

    db.query(PracticeReport).filter(PracticeReport.submission_id == submission_id).delete(synchronize_session=False)
    db.query(AiTask).filter(AiTask.business_id == submission_id).delete(synchronize_session=False)
    db.query(PracticeSubmission).filter(PracticeSubmission.id == submission_id).delete(synchronize_session=False)
    db.commit()
    return True


def _format_duration(value: float | None) -> str:
    """把视频秒数格式化为页面和报告里的中文显示。"""

    if value is None:
        return "未填写"
    if value.is_integer():
        return f"{int(value)} 秒"
    return f"{value:.1f} 秒"


def _markdown_list(items: list[str]) -> str:
    """把字符串列表渲染成 Markdown 列表。"""

    if not items:
        return "- 暂无"
    return "\n".join(f"- {item}" for item in items)


def _issue_markdown(items: list[dict]) -> str:
    """把结构化观察点渲染成 Markdown。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('category', '观察点')}**：{item.get('description', '')}")
        suggestion = item.get("suggestion")
        if suggestion:
            lines.append(f"  - 建议：{suggestion}")
    return "\n".join(lines)
