import os
import sys
from pathlib import Path
from app import create_app
from app.config import Config


# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

app = create_app(Config)


if __name__ == '__main__':
    app.run(debug=True)