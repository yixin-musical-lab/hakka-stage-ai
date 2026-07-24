from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.routes.auth import router as auth_router
from app.api.routes.class_interactions import router as class_interaction_router
from app.api.routes.llm_options import router as llm_options_router
from app.api.routes.lesson_plans import router as lesson_plan_router
from app.api.routes.media_generations import router as media_generation_router
from app.api.routes.media_studio import public_router as media_studio_public_router
from app.api.routes.media_studio import router as media_studio_router
from app.api.routes.motion_transfer import public_router as motion_transfer_public_router
from app.api.routes.motion_transfer import router as motion_transfer_router
from app.api.routes.movement_guides import router as movement_guide_router
from app.api.routes.musical import router as musical_router
from app.api.routes.practice import router as practice_router
from app.api.routes.rehearsal_reviews import router as rehearsal_review_router
from app.api.routes.system import router as system_router
from app.api.routes.workspace_overview import router as workspace_overview_router

api_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_current_user)])

# 统一在这里汇总后端路由，main.py 只需要挂载一个总路由。
# 后续新增课堂互动、示范材料、课后练习等模块时，只在本文件注册即可。
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(media_studio_public_router)
api_router.include_router(motion_transfer_public_router)

# 健康检查和登录保持公开；账号创建接口在自身路由中显式依赖当前用户。
# 其余业务接口在总路由层统一要求 Bearer 令牌，避免新模块漏加鉴权。
protected_router.include_router(llm_options_router)
protected_router.include_router(lesson_plan_router)
protected_router.include_router(class_interaction_router)
protected_router.include_router(musical_router)
protected_router.include_router(movement_guide_router)
protected_router.include_router(media_generation_router)
protected_router.include_router(practice_router)
protected_router.include_router(rehearsal_review_router)
protected_router.include_router(workspace_overview_router)
protected_router.include_router(media_studio_router)
protected_router.include_router(motion_transfer_router)
api_router.include_router(protected_router)
