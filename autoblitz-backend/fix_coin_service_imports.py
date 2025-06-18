#!/usr/bin/env python3
"""
coin_service.py import 구문 수정
"""

import re

# 파일 읽기
with open('app/services/coin/coin_service.py', 'r') as f:
    content = f.read()

# import 구문 수정
content = re.sub(
    r'from \.\.\.?\.?exchanges\.okx\.core\.api_client_test',
    'import sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))\nfrom app.exchanges.okx.core.api_client_test',
    content
)

# 파일 쓰기
with open('app/services/coin/coin_service.py', 'w') as f:
    f.write(content)

print("✅ coin_service.py import 구문 수정 완료")
