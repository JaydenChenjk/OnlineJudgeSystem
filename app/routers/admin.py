from fastapi import APIRouter, Request
from ..models import data_store
from ..auth import require_admin

router = APIRouter(prefix="/api", tags=["admin"])

# 重置功能已移至 import_export 路由 