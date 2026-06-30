from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models import AiTask, PracticeReport, PracticeSubmission
from app.schemas import (
    PracticeAnalyzeResponse,
    PracticeReportResponse,
    PracticeReportReviewRequest,
    PracticeSubmissionCreateRequest,
    PracticeSubmissionDetailResponse,
    PracticeSubmissionSummaryResponse,
    PracticeVideoUploadResponse,
)
from app.services.practice_service import (
    create_submission_from_request,
    delete_practice_submission_with_related_data,
    render_practice_report_markdown,
    report_response,
    review_practice_report,
    submission_detail,
    submission_summary,
    upsert_basic_practice_report,
)
from app.services.practice_upload_service import PracticeUploadError, save_practice_video_upload

router = APIRouter(prefix="/api", tags=["practice"])


@router.post(
    "/practice-submissions",
    response_model=PracticeSubmissionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="提交课后练习视频记录",
)
def create_practice_submission(
    request: PracticeSubmissionCreateRequest,
    db: Session = Depends(get_db),
) -> PracticeSubmissionDetailResponse:
    """创建学生练习提交记录。

    第一阶段用视频 URL / 对象地址表示“已上传视频”，暂不在 API 服务里直接保存大文件。
    """

    submission = create_submission_from_request(request)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission_detail(db, submission)


@router.post(
    "/practice-submissions/upload",
    response_model=PracticeVideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传课后练习视频文件",
)
def upload_practice_video(
    request: Request,
    file: UploadFile = File(..., description="学生录制的 15-60 秒练习视频文件"),
    settings: Settings = Depends(get_settings),
) -> PracticeVideoUploadResponse:
    """保存练习视频并返回可回填到提交记录的视频地址。

    第一阶段使用开发期本地目录承接上传，避免在 API 服务里引入 MinIO SDK；后续对象存储接入后，
    可保持接口路径和响应字段不变，只替换底层保存逻辑。
    """

    try:
        result = save_practice_video_upload(
            file=file,
            upload_root=Path(settings.practice_upload_dir),
            max_bytes=settings.practice_max_upload_bytes,
        )
    except PracticeUploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    base_url = str(request.base_url).rstrip("/")
    return PracticeVideoUploadResponse(
        url=f"{base_url}/uploads/{result.relative_path}",
        original_file_name=result.original_file_name,
        stored_file_name=result.stored_file_name,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
    )


@router.get(
    "/practice-submissions",
    response_model=list[PracticeSubmissionSummaryResponse],
    summary="查询课后练习提交列表",
)
def list_practice_submissions(db: Session = Depends(get_db)) -> list[PracticeSubmissionSummaryResponse]:
    """按更新时间倒序返回学生练习提交摘要，供老师集中复核。"""

    submissions = db.query(PracticeSubmission).order_by(desc(PracticeSubmission.updated_at)).all()
    return [submission_summary(db, submission) for submission in submissions]


@router.get(
    "/practice-submissions/{submission_id}",
    response_model=PracticeSubmissionDetailResponse,
    summary="读取课后练习提交详情",
)
def get_practice_submission(submission_id: UUID, db: Session = Depends(get_db)) -> PracticeSubmissionDetailResponse:
    """返回练习提交信息和当前练习观察报告。"""

    submission = db.get(PracticeSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习提交不存在。")
    return submission_detail(db, submission)


@router.post(
    "/practice-submissions/{submission_id}/analyze",
    response_model=PracticeAnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="生成课后练习基础观察报告",
)
def analyze_practice_submission(submission_id: UUID, db: Session = Depends(get_db)) -> PracticeAnalyzeResponse:
    """生成第一阶段基础观察报告。

    这里仅创建可复核的报告草稿和 SUCCESS 状态任务，不执行 RTMPose / DTW / LLM 重型链路。
    """

    submission = db.get(PracticeSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习提交不存在。")

    now = datetime.utcnow()
    report = upsert_basic_practice_report(db, submission)
    task = AiTask(
        task_type="practice_submission.basic_observation",
        status="SUCCESS",
        progress=100,
        business_id=submission.id,
        input_snapshot={
            "submission_id": str(submission.id),
            "video_url": submission.video_url,
            "reference_video_url": submission.reference_video_url,
            "evaluation_focus": submission.evaluation_focus,
        },
        result_id=report.id,
        started_at=now,
        finished_at=now,
    )
    db.add(task)
    db.commit()

    return PracticeAnalyzeResponse(
        task_id=task.id,
        submission_id=submission.id,
        report_id=report.id,
        status="SUCCESS",
        message="练习基础观察报告已生成；真实姿态估计、DTW 对齐和 LLM 报告后续接入 Worker。",
    )


@router.get(
    "/practice-reports/{report_id}",
    response_model=PracticeReportResponse,
    summary="读取课后练习观察报告",
)
def get_practice_report(report_id: UUID, db: Session = Depends(get_db)) -> PracticeReportResponse:
    """读取单份练习观察报告。"""

    report = db.get(PracticeReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习报告不存在。")
    return report_response(report)


@router.put(
    "/practice-reports/{report_id}/review",
    response_model=PracticeReportResponse,
    summary="保存老师复核后的练习报告",
)
def review_report(
    report_id: UUID,
    request: PracticeReportReviewRequest,
    db: Session = Depends(get_db),
) -> PracticeReportResponse:
    """保存老师确认稿和最终点评，供学生查看。"""

    report = db.get(PracticeReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习报告不存在。")

    updated = review_practice_report(
        db=db,
        report=report,
        edited_content=request.edited_content,
        teacher_feedback=request.teacher_feedback,
        reviewed_by=request.reviewed_by,
    )
    db.commit()
    db.refresh(updated)
    return report_response(updated)


@router.get(
    "/practice-reports/{report_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出课后练习观察报告 Markdown",
)
def export_practice_report_markdown(report_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用老师复核稿。"""

    report = db.get(PracticeReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习报告不存在。")

    markdown = render_practice_report_markdown(report)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="练习报告尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/practice-submissions/{submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除课后练习提交",
)
def delete_practice_submission(submission_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除练习提交、关联报告和本次基础观察任务。"""

    deleted = delete_practice_submission_with_related_data(db, submission_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习提交不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
