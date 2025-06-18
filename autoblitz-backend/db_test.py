#!/usr/bin/env python3
"""데이터베이스 연결 테스트"""

import sqlite3
import os

def test_database():
    """데이터베이스 테스트"""
    try:
        # 1. 파일 존재 확인
        if os.path.exists('autoblitz.db'):
            size = os.path.getsize('autoblitz.db')
            print(f"✅ DB 파일 존재: {size:,} bytes")
        else:
            print("❌ autoblitz.db 파일 없음")
            return False
        
        # 2. 연결 테스트
        with sqlite3.connect('autoblitz.db') as conn:
            cursor = conn.cursor()
            
            # 테이블 목록 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"✅ 테이블 수: {len(tables)}개")
            
            if tables:
                print("📋 테이블 목록:")
                for table in tables:
                    print(f"   - {table[0]}")
            
            # 봇 테이블 확인
            try:
                cursor.execute("SELECT COUNT(*) FROM bots;")
                bot_count = cursor.fetchone()[0]
                print(f"✅ 봇 레코드: {bot_count}개")
            except:
                print("⚠️ 봇 테이블 없음 (정상)")
            
            # 사용자 테이블 확인
            try:
                cursor.execute("SELECT COUNT(*) FROM users;")
                user_count = cursor.fetchone()[0]
                print(f"✅ 사용자 레코드: {user_count}개")
            except:
                print("⚠️ 사용자 테이블 없음 (정상)")
            
            return True
            
    except Exception as e:
        print(f"❌ DB 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("💾 데이터베이스 연결 테스트")
    print("=" * 30)
    
    if test_database():
        print("\n🎉 DB 테스트 통과!")
        print("💡 다음: Step 5로 진행하세요")
    else:
        print("\n❌ DB 테스트 실패")
