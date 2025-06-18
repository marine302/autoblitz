# 파일 경로: /workspaces/autoblitz/autoblitz-backend/app/exchanges/okx/timestamp_fix.py

"""
OKX API 타임스탬프 수정 패치
live_client.py의 타임스탬프 형식을 수정합니다.
"""

import os

def fix_timestamp_in_live_client():
    """live_client.py의 타임스탬프 형식 수정"""
    
    file_path = "app/exchanges/okx/live_client.py"
    
    # 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 수정 전
    old_code1 = 'timestamp = str(int(time.time() * 1000))'
    # 수정 후
    new_code1 = 'timestamp = datetime.utcnow().strftime(\'%Y-%m-%dT%H:%M:%S.%f\')[:-3] + \'Z\''
    
    # 수정 전
    old_code2 = 'import time'
    # 수정 후  
    new_code2 = 'import time\nfrom datetime import datetime'
    
    # 코드 수정
    content = content.replace(old_code1, new_code1)
    content = content.replace(old_code2, new_code2)
    
    # 백업 생성
    backup_path = file_path + '.backup_timestamp'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 수정된 내용 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 타임스탬프 형식 수정 완료!")
    print(f"백업 파일: {backup_path}")
    
    # 수정 내용 확인
    print("\n수정된 부분:")
    print("1. datetime import 추가")
    print("2. 타임스탬프를 ISO 8601 형식으로 변경")
    print("   예: 2024-06-18T10:30:00.123Z")

if __name__ == "__main__":
    fix_timestamp_in_live_client()