"""健康检查路由"""

from fastapi import APIRouter, Request, status
from app.utils.problem_detail import Errors

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """健康检查 - 返回服务状态和模型加载状态"""
    
    services_status = {}
    
    if hasattr(request.app.state, 'milvus_service') and request.app.state.milvus_service:
        services_status['milvus'] = {
            'status': 'loaded',
            'connected': True,
        }
    else:
        services_status['milvus'] = {
            'status': 'not_loaded',
            'connected': False,
        }
    
    if hasattr(request.app.state, 'reranker_service') and request.app.state.reranker_service:
        reranker = request.app.state.reranker_service
        services_status['reranker'] = {
            'status': 'loaded',
            'model': reranker.MODEL_NAME,
            'device': reranker.device,
            'initialized': reranker._initialized,
        }
    else:
        services_status['reranker'] = {
            'status': 'not_loaded',
        }
    
    if hasattr(request.app.state, 'embedding_service') and request.app.state.embedding_service:
        embedding = request.app.state.embedding_service
        model_info = embedding.get_model_info()
        services_status['embedding'] = {
            'status': 'loaded',
            'model': model_info.get('name', 'unknown'),
            'type': model_info.get('type', 'unknown'),
            'dimension': model_info.get('dimension', 'unknown'),
            'device': getattr(embedding, 'device', 'unknown'),
            'initialized': embedding.is_loaded(),
        }
    else:
        services_status['embedding'] = {
            'status': 'not_loaded',
        }
    
    all_loaded = all(
        s.get('status') in ['loaded', 'available'] 
        for s in services_status.values()
    )
    
    return {
        "status": "ok" if all_loaded else "degraded",
        "service": "scholarai-ai",
        "models": services_status,
    }
