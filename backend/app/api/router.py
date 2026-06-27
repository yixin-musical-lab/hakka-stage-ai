from fastapi import APIRouter

from app.api.routes.llm_options import router as llm_options_router
from app.api.routes.lesson_plans import router as lesson_plan_router
from app.api.routes.system import router as system_router

api_router = APIRouter()

# 统一在这里汇总后端路由，main.py 只需要挂载一个总路由。
# 后续新增课堂互动、示范材料、课后练习等模块时，只在本文件注册即可。
api_router.include_router(system_router)
api_router.include_router(llm_options_router)
api_router.include_router(lesson_plan_router)
