from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PracticeSubmissionCreateRequest(BaseModel):
    """T06 学生练习提交请求。

    第一阶段用视频 URL 或对象存储地址代表“已上传视频”，暂不在 API 服务里直接处理视频文件。
    字段名保持英文，中文描述用于保证 OpenAPI 文档对课程组和前端同学可读。
    """

    course_title: str = Field("", max_length=200, description="课程或剧目片段名称，例如：客家山歌主题舞蹈体验课")
    task_title: str = Field(..., min_length=1, max_length=200, description="练习任务标题，例如：30 秒客家山歌律动打卡")
    task_description: str = Field("", max_length=1600, description="老师布置的练习要求")
    student_name: str = Field(..., min_length=1, max_length=80, description="学生姓名或演示学生代号")
    student_group: str = Field("", max_length=120, description="班级、小组或角色分组")
    video_url: str = Field(..., min_length=1, max_length=1200, description="练习视频访问地址，后续可替换为 MinIO 对象地址")
    video_file_name: str = Field("", max_length=240, description="原始视频文件名，便于老师核对")
    video_duration_seconds: float | None = Field(None, ge=0, le=600, description="视频时长，单位秒；建议 15-60 秒")
    video_notes: str = Field("", max_length=1200, description="学生补充说明，例如拍摄环境或练习次数")
    reference_action_name: str = Field("", max_length=160, description="对应标准动作名称，例如：双手打开转身")
    reference_video_url: str = Field("", max_length=1200, description="标准动作参考视频地址；为空时仅生成基础观察报告")
    evaluation_focus: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="老师关注的评价重点，例如：节奏、完整度、动作稳定、全身入镜",
    )


class PracticeVideoUploadResponse(BaseModel):
    """练习视频上传结果。

    url 可直接回填到练习提交记录；当前 storage_mode 为 local_dev，后续替换 MinIO 后保持字段稳定。
    """

    url: str = Field(..., description="练习视频可访问地址，前端会回填到提交表单")
    original_file_name: str = Field(..., description="学生上传的原始文件名")
    stored_file_name: str = Field(..., description="服务端保存后的安全文件名")
    content_type: str = Field(..., description="上传文件的 MIME 类型")
    size_bytes: int = Field(..., ge=1, description="上传文件大小，单位字节")
    storage_mode: Literal["local_dev"] = Field("local_dev", description="当前存储模式；第一阶段使用本地开发目录")


class PracticeSubmissionSummaryResponse(BaseModel):
    """练习提交列表摘要。"""

    id: UUID
    course_title: str
    task_title: str
    student_name: str
    student_group: str
    status: str
    report_status: str | None
    analysis_mode: str | None
    created_at: datetime
    updated_at: datetime


class PracticeIssuePoint(BaseModel):
    """练习报告中的一个结构化观察点。"""

    category: str = Field(..., min_length=1, max_length=80, description="观察类别，例如：拍摄质量、节奏、动作完整度")
    description: str = Field(..., min_length=1, max_length=500, description="观察到的问题或现象")
    suggestion: str = Field("", max_length=500, description="给学生或老师的改进建议")


class PracticeReportContent(BaseModel):
    """练习辅助观察报告正文。

    该结构只表达“观察建议”和“老师复核点”，不输出专业动作正确率或自动判分。
    """

    title: str = Field(..., min_length=1, max_length=200, description="报告标题")
    observation_mode: Literal["basic_observation", "reference_comparison_pending", "reference_comparison"] = Field(
        "basic_observation",
        description="报告模式：基础观察、等待标准动作对比或标准动作对比",
    )
    summary: str = Field("", max_length=1200, description="本次练习总体观察摘要")
    video_basic_info: list[str] = Field(default_factory=list, description="视频基本信息")
    shooting_quality_feedback: list[str] = Field(default_factory=list, description="拍摄质量反馈")
    rhythm_and_completion_observations: list[str] = Field(default_factory=list, description="节奏与完整度观察")
    posture_and_stability_observations: list[str] = Field(default_factory=list, description="姿态和动作稳定性观察")
    structured_issue_points: list[PracticeIssuePoint] = Field(default_factory=list, description="结构化观察点")
    ai_suggestions: list[str] = Field(default_factory=list, description="系统整理出的练习建议")
    teacher_review_points: list[str] = Field(default_factory=list, description="建议老师重点复核的内容")
    next_practice_tasks: list[str] = Field(default_factory=list, description="下一次练习小任务")
    teacher_final_comment: str = Field("", max_length=1600, description="老师最终点评")
    boundary_note: str = Field("", max_length=1200, description="能力边界说明，避免误解为专业自动判分")


class PracticeReportResponse(BaseModel):
    """练习报告详情响应。"""

    id: UUID
    submission_id: UUID
    title: str
    status: str
    analysis_mode: str
    content: PracticeReportContent | None
    edited_content: PracticeReportContent | None
    teacher_feedback: str
    reviewed_by: str
    reviewed_at: datetime | None
    raw_analysis_info: dict | None
    created_at: datetime
    updated_at: datetime


class PracticeSubmissionDetailResponse(BaseModel):
    """练习提交详情，包含当前报告。"""

    id: UUID
    course_title: str
    task_title: str
    task_description: str
    student_name: str
    student_group: str
    video_url: str
    video_file_name: str
    video_duration_seconds: float | None
    video_notes: str
    reference_action_name: str
    reference_video_url: str
    evaluation_focus: list[str]
    status: str
    report: PracticeReportResponse | None
    created_at: datetime
    updated_at: datetime


class PracticeAnalyzeResponse(BaseModel):
    """触发练习分析后的响应。"""

    task_id: UUID
    submission_id: UUID
    report_id: UUID
    status: Literal["SUCCESS"]
    message: str


class PracticeReportReviewRequest(BaseModel):
    """老师复核练习报告请求。"""

    edited_content: PracticeReportContent = Field(..., description="老师确认或修改后的报告正文")
    teacher_feedback: str = Field("", max_length=1600, description="老师最终点评，保存后学生可查看")
    reviewed_by: str = Field("demo-teacher", max_length=80, description="复核老师姓名或演示账号")
