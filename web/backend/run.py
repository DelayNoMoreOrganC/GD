import uvicorn

from app.config import get_settings


if __name__ == "__main__":
    s = get_settings()
    print("=" * 50)
    print("  案件归档系统 V5 Web")
    print("=" * 50)
    print("  后端地址: http://{}:{}".format(s.host, s.port))
    print("  前端页面: http://{}:{}".format(s.host, s.port))
    print("  API:      http://{}:{}/api/health".format(s.host, s.port))
    print("  默认账号: {} / {}".format(s.bootstrap_admin_user, s.bootstrap_admin_password))
    print("  律师账号: zgls / zgls123")
    print("=" * 50)
    uvicorn.run("app.main:app", host=s.host, port=s.port, reload=False, workers=1)
