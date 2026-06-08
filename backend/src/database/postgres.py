"""
PostgreSQL 数据库配置
HPU项目统一使用PostgreSQL
"""

import os
from typing import Optional

# 读取 .env 文件
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())


class PostgresConfig:
    """
    PostgreSQL配置管理器
    
    连接方式:
    1. 环境变量 PG_* 组合
    2. DATABASE_URL 直接指定
    3. 默认本地配置
    """
    
    def __init__(self):
        self.env = os.getenv('HPU_ENV', 'development')
    
    def get_connection_params(self) -> dict:
        """
        获取连接参数
        
        默认值:
        - 主机: localhost
        - 端口: 5432
        - 数据库: hpu_db
        - 用户: postgres
        - 密码: winson
        """
        # 方式1: 直接URL
        if os.getenv('DATABASE_URL'):
            return self._parse_url(os.getenv('DATABASE_URL'))
        
        # 方式2: 分别指定
        host = os.getenv('PG_HOST', 'localhost')
        port = int(os.getenv('PG_PORT', '5432'))
        database = os.getenv('PG_DATABASE', 'hpu_db')
        user = os.getenv('PG_USER', 'postgres')
        password = os.getenv('PG_PASSWORD', 'winson')
        
        return {
            "type": "postgresql",
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "url": f"postgresql://{user}:{password}@{host}:{port}/{database}"
        }
    
    def _parse_url(self, url: str) -> dict:
        """解析URL"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        return {
            "type": "postgresql",
            "host": parsed.hostname or 'localhost',
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip('/') or 'hpu_db',
            "user": parsed.username or 'postgres',
            "password": parsed.password or '',
            "url": url
        }
    
    def get_sqlalchemy_url(self) -> str:
        """获取SQLAlchemy连接URL"""
        params = self.get_connection_params()
        return params["url"]
    
    def get_navicat_config(self) -> dict:
        """
        Navicat连接配置
        """
        params = self.get_connection_params()
        return {
            "connection_name": "HPU_PostgreSQL",
            "host": params["host"],
            "port": params["port"],
            "username": params["user"],
            "password": params["password"],
            "database": params["database"] if params["database"] else ""
        }


# =============================================================================
# 快速初始化
# =============================================================================

def init_postgres():
    """
    初始化PostgreSQL数据库
    
    使用方法:
    1. 确保PostgreSQL已安装并运行
    2. 创建数据库: CREATE DATABASE hpu_db;
    3. 设置密码: set PG_PASSWORD=你的密码
    4. 运行: python -c "from src.database.postgres import init_postgres; init_postgres()"
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    config = PostgresConfig()
    url = config.get_sqlalchemy_url()
    params = config.get_connection_params()
    
    print(f"[HPU] 连接类型: {params['type']}")
    print(f"[HPU] 数据库: {params['database']}")
    
    try:
        # 创建引擎
        engine = create_engine(
            url,
            echo=True,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
        
        # 测试连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"[HPU] ✅ 连接成功!")
            print(f"[HPU] PostgreSQL版本: {version[:50]}...")
        
        # 创建表
        print("[HPU] 创建数据表...")
        from src.database.models import Base
        Base.metadata.create_all(engine)
        print("[HPU] ✅ 表创建完成")
        
        # 初始化提示词
        print("[HPU] 初始化提示词模板...")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        from src.database.models import seed_prompt_templates
        seed_prompt_templates(session)
        session.close()
        print("[HPU] ✅ 提示词模板初始化完成")
        
        print("\n" + "="*50)
        print("🎉 数据库初始化完成!")
        print("="*50)
        
        # Navicat配置
        navicat = config.get_navicat_config()
        print("\n📋 Navicat连接配置:")
        for k, v in navicat.items():
            if k != 'password':
                print(f"   {k}: {v}")
        
        return engine
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        print("\n请检查:")
        print("  1. PostgreSQL是否已安装并运行?")
        print("  2. 数据库hpu_db是否已创建?")
        print("  3. 用户名密码是否正确?")
        print("\n设置密码: set PG_PASSWORD=你的密码")
        raise


def check_connection() -> bool:
    """
    检查数据库连接
    
    Returns:
        True: 连接成功
        False: 连接失败
    """
    try:
        from sqlalchemy import create_engine, text
        
        config = PostgresConfig()
        url = config.get_sqlalchemy_url()
        engine = create_engine(url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return True
    except Exception:
        return False


# =============================================================================
# 安装指南
# =============================================================================

INSTALL_GUIDE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                   PostgreSQL 安装指南 (Windows)                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

【方法1: winget 安装】(推荐)
──────────────────────────────────────────────────────────────────────────────

1. 打开PowerShell (管理员)

2. 运行:
   winget install PostgreSQL.PostgreSQL

3. 安装过程中设置postgres用户密码 (记住!)

4. 验证安装:
   psql --version


【方法2: 官网下载】
──────────────────────────────────────────────────────────────────────────────

1. 访问: https://www.postgresql.org/download/windows/
2. 下载最新版 installer (exe文件)
3. 一路Next，设置postgres密码


【创建数据库】
──────────────────────────────────────────────────────────────────────────────

打开PowerShell或pgAdmin:

1. 连接:
   psql -U postgres -h localhost
   (输入密码)

2. 创建数据库:
   CREATE DATABASE hpu_db;

3. 确认:
   \\l

4. 退出:
   \\q


【Navicat连接配置】
──────────────────────────────────────────────────────────────────────────────

1. 打开Navicat
2. 连接 → PostgreSQL
3. 填入:

   连接名: HPU_Local
   主机:   localhost
   端口:   5432
   用户名: postgres
   密码:   [你设置的密码]
   数据库: hpu_db

4. 测试连接 → 成功!


【Python环境配置】
──────────────────────────────────────────────────────────────────────────────

1. 安装驱动:
   pip install psycopg2-binary sqlalchemy

2. 设置密码:
   set PG_PASSWORD=你的密码

3. 测试连接:
   python -c "from src.database.postgres import check_connection; print('OK' if check_connection() else 'FAIL')"

4. 初始化数据库:
   python -c "from src.database.postgres import init_postgres; init_postgres()"
"""


if __name__ == "__main__":
    print(INSTALL_GUIDE)
