"""런처 크레딧(CreditUI.arc CreditStaff_SL0_jpn) 번역 → launcher/ko_credits.json.
일본어 칸도 영어로 되어 있다. 직함·부서명(보라색 줄)과 안내 문구만 한국어로 옮기고, 인명·회사명·곡명은 그대로 둔다.
    python tools/credits_ko.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmd  # noqa: E402
import mtarc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'romNX', 'CreditUI.arc')
OUT = os.path.join(ROOT, 'launcher', 'ko_credits.json')
P = '<ID_COLOR_PURPLE><ID_SIZE_SMALL>'
S = '<ID_SIZE_SMALL>'

TITLE = {
    'DIRECTOR': '디렉터', 'GAME DESIGNER': '게임 디자이너', 'TECHNICAL PROGRAMMER': '테크니컬 프로그래머',
    'UX DESIGNER': 'UX 디자이너', 'VFX DESIGNERS': 'VFX 디자이너', 'AUDIO DIRECTOR': '오디오 디렉터',
    'MUSIC COMPOSER': '작곡', 'SOUND PROGRAMMER': '사운드 프로그래머', 'SOUND DESIGNER': '사운드 디자이너',
    'CHASERS': '체이서', 'RELEASE MANAGER': '릴리스 매니저', 'SUBMISSION COORDINATORS': '서브미션 코디네이터',
    'LOGO DESIGN': '로고 디자인', 'GRAPHIC DESIGNER': '그래픽 디자이너', 'PROJECT MANAGER': '프로젝트 매니저',
    'MT FRAMEWORK DEVELOPMENT TEAM': 'MT 프레임워크 개발팀', 'VIDEO UPCONVERSION': '영상 업컨버전',
    'SENIOR MANAGER OF GLOBAL PRODUCTION': '글로벌 프로덕션 시니어 매니저',
    'LOCALIZATION COORDINATOR': '로컬라이제이션 코디네이터',
    'LOCALIZATION SOLUTIONS DEVELOPER': '로컬라이제이션 솔루션 개발',
    'LOCALIZATION DIRECTOR &': '로컬라이제이션 디렉터 &', 'ENGLISH LOCALIZATION': '영어 로컬라이제이션',
    'ENGLISH EDITOR': '영어 에디터', 'FRENCH LOCALIZATION': '프랑스어 로컬라이제이션', 'FRENCH EDITOR': '프랑스어 에디터',
    'ITALIAN LOCALIZATION': '이탈리아어 로컬라이제이션', 'ITALIAN EDITOR': '이탈리아어 에디터',
    'GERMAN LOCALIZATION': '독일어 로컬라이제이션', 'GERMAN EDITOR': '독일어 에디터',
    'SPANISH LOCALIZATION': '스페인어 로컬라이제이션', 'SPANISH EDITOR': '스페인어 에디터',
    'CHINESE LOCALIZATION & CHINESE EDITOR': '중국어 로컬라이제이션 & 에디터',
    'CAPCOM TAIWAN LOCALIZATION TEAM': '캡콤 타이완 로컬라이제이션 팀',
    'QA MANAGER': 'QA 매니저', 'LEAD TESTER': '리드 테스터', 'ASSISTANT LEAD TESTERS': '어시스턴트 리드 테스터',
    'COMPLIANCE TESTERS': '컴플라이언스 테스터', 'NETWORK TESTER': '네트워크 테스터', 'TESTERS': '테스터',
    'QA CONTENTS ANALYSIS TEAM': 'QA 콘텐츠 분석팀', 'PROGRESS CONTROL TEAM': '진행 관리팀',
    'PROMOTION': '프로모션', 'PUBLICITY': '홍보', 'OFFICIAL WEBSITE CREATORS': '공식 웹사이트 제작',
    'ROCKMAN UNITY BLOG EDITOR &': '록맨 유니티 블로그 편집 &', 'INTERACTIVE PR': '인터랙티브 PR',
    'DIGITAL MARKETING STRATEGY AND PLANNING': '디지털 마케팅 전략·기획', 'SALES STRATEGY PLANNING': '판매 전략 기획',
    'SALES PROMOTIONAL TOOL PLANNING': '판촉물 기획', 'e-CAPCOM': 'e-CAPCOM', 'CUSTOMER SUPPORT': '고객 지원',
    'CAPCOM TV!': 'CAPCOM TV!', 'ADVERTISING DESIGN': '광고 디자인', 'PRODUCER': '프로듀서',
    'PROGRAMMING DIRECTOR': '프로그래밍 디렉터', 'PROGRAMMERS': '프로그래머', 'SPECIAL THANKS': '스페셜 땡스',
    'LEAD PROGRAMMER': '리드 프로그래머', 'DESIGNERS': '디자이너',
    'CHIEF EXECUTIVE OFFICER': '최고경영자', 'CHIEF OPERATING OFFICER': '최고운영책임자',
    'HEAD OF MARKETING': '마케팅 총괄', 'SENIOR BRAND MARKETING MANAGER': '시니어 브랜드 마케팅 매니저',
    'BRAND MARKETING MANAGER': '브랜드 마케팅 매니저', 'MARKETING ADMINISTRATIVE ASSISTANT': '마케팅 행정 어시스턴트',
    'SENIOR DIRECTOR, COMMUNICATIONS': '커뮤니케이션 시니어 디렉터', 'SENIOR PR SPECIALIST': '시니어 PR 스페셜리스트',
    'ASSOCIATE MANAGER, SOCIAL MEDIA & COMMUNITY': '소셜 미디어·커뮤니티 어소시에이트 매니저',
    'SENIOR DIRECTOR, DIVISIONAL COMMUNICATIONS': '부문 커뮤니케이션 시니어 디렉터',
    'ASSOCIATE PROJECT MANAGER': '어소시에이트 프로젝트 매니저', 'VICE PRESIDENT, SALES': '영업 부사장',
    'SENIOR NATIONAL SALES DIRECTOR': '시니어 내셔널 세일즈 디렉터', 'AREA SALES MANAGERS': '지역 세일즈 매니저',
    'SENIOR MANAGER, CHANNEL MARKETING &': '채널 마케팅 & 소비자 상품', 'CONSUMER PRODUCTS': '시니어 매니저',
    'SENIOR VICE PRESIDENT, DIGITAL PLATFORMS': '디지털 플랫폼 수석 부사장',
    'MANAGER, BUSINESS DEVELOPMENT': '사업 개발 매니저', 'DIGITAL ACCOUNT MANAGER': '디지털 어카운트 매니저',
    'DIGITAL SALES MANAGER': '디지털 세일즈 매니저', 'BUSINESS STRATEGY ANALYST': '사업 전략 애널리스트',
    'MANAGER, STRATEGIC PLANNING': '전략 기획 매니저',
    'ASSOCIATE MANAGER, STRATEGIC PLANNING &': '전략 기획 & 경영 관리', 'CORPORATE ADMINISTRATION': '어소시에이트 매니저',
    'ASSOCIATE MANAGER, STRATEGIC PLANNING': '전략 기획 어소시에이트 매니저',
    'SENIOR DIRECTOR, CREATIVE SERVICES & EVENTS': '크리에이티브 서비스·이벤트 시니어 디렉터',
    'SENIOR EVENTS MANAGER': '시니어 이벤트 매니저', 'EVENTS MANAGER': '이벤트 매니저',
    'PROJECT MANAGER, CREATIVE SERVICES': '크리에이티브 서비스 프로젝트 매니저',
    'SENIOR GRAPHIC DESIGNER': '시니어 그래픽 디자이너', 'DIRECTOR, LICENSING': '라이선스 디렉터',
    'LICENSING OPERATIONS MANAGER': '라이선스 운영 매니저', 'ASSOCIATE LICENSING MANAGER': '어소시에이트 라이선스 매니저',
    'DIRECTOR, PRODUCT OPS & SUBMISSIONS': '제품 운영·서브미션 디렉터',
    'ASSOCIATE PROJECT MANAGERS': '어소시에이트 프로젝트 매니저', 'DEVELOPMENT SUPPORT TECHNICIAN': '개발 지원 기술자',
    'BRAZIL TERRITORY DIRECTOR, SALES & MARKETING': '브라질 지역 세일즈·마케팅 디렉터',
    'BRAZIL PR MANAGER': '브라질 PR 매니저', 'BRAZIL COMMUNITY MANAGER': '브라질 커뮤니티 매니저',
    'CEO': '최고경영자', 'COO': '최고운영책임자', 'MARKETING DIRECTOR': '마케팅 디렉터',
    'DIRECTOR, BUSINESS SERVICES': '비즈니스 서비스 디렉터', 'BRAND MANAGER': '브랜드 매니저',
    'LICENSING CO-ORDINATOR': '라이선스 코디네이터', 'COMMUNITY MANAGER': '커뮤니티 매니저',
    'DIGITAL SALES ACCOUNT MANAGER': '디지털 세일즈 어카운트 매니저', 'DIGITAL & MOBILE SALES MANAGER': '디지털·모바일 세일즈 매니저',
    'PRODUCTION SERVICES MANAGER': '프로덕션 서비스 매니저', 'RESEARCH & PLANNING MANAGER': '리서치·기획 매니저',
    'MARKETING SERVICES MANAGER': '마케팅 서비스 매니저', 'LEGAL MANAGER': '법무 매니저',
    'PRODUCTION SERVICES CO-ORDINATOR': '프로덕션 서비스 코디네이터', 'BUSINESS SERVICES MANAGERS': '비즈니스 서비스 매니저',
    'SENIOR PR MANAGER': '시니어 PR 매니저', 'RESEARCH & PLANNING ASSISTANT': '리서치·기획 어시스턴트',
    'COMMUNICATIONS MANAGER': '커뮤니케이션 매니저', 'MARKETING MANAGER': '마케팅 매니저',
    'COMMERICAL DIRECTOR': '커머셜 디렉터', 'PR MANAGER': 'PR 매니저', 'SALES & MARKETING DIRECTOR': '세일즈·마케팅 디렉터',
    'BUSINESS DEVELOPMENT MANAGER': '사업 개발 매니저', 'MARKETING COORDINATOR': '마케팅 코디네이터',
    'MARKETING EXECUTIVE': '마케팅 이그제큐티브', 'ILLUSTRATION': '일러스트', 'ULTIMATE REMIX STAFF': '얼티밋 리믹스 스태프',
    'SERIES PRODUCER': '시리즈 프로듀서', 'EXECUTIVE PRODUCER': '총괄 프로듀서',
}
SMALL = {
    'Font Design by Fontworks Inc.': '폰트 디자인: Fontworks Inc.',
    'Special Thanks: Founder Electronics Corp., Ltd. &': '스페셜 땡스: Founder Electronics Corp., Ltd. &',
    'The typefaces included herein are solely': '여기에 사용된 서체는',
    'developed by DynaComware.': 'DynaComware 가 단독으로 개발했습니다.',
    'SUPPORTED BY': '협력',
    'Drums': '드럼',
}
OTHER = {'<ID_COLOR_PURPLE><ID_SIZE_MEDIUM>AND YOU!': '<ID_COLOR_PURPLE><ID_SIZE_MEDIUM>그리고 당신!'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d, _, _, es = mtarc.parse(ARC)
    g = [gmd.Gmd(mtarc.blob(d, e)) for e in es if e['name'].endswith('CreditStaff_SL0_jpn')][0]
    out, unused_t, unused_s = {}, set(TITLE), set(SMALL)
    for t in g.texts:
        if t.startswith(P):
            body = t[len(P):]
            if body not in TITLE:
                raise SystemExit(f'번역 없는 직함: {body!r}')
            if TITLE[body] != body:
                out[t] = P + TITLE[body]
            unused_t.discard(body)
        elif t.startswith(S) and t[len(S):] in SMALL:
            out[t] = S + SMALL[t[len(S):]]
            unused_s.discard(t[len(S):])
        elif t in OTHER:
            out[t] = OTHER[t]
    assert not unused_t and not unused_s, (unused_t, unused_s)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('크레딧 번역', len(out))


if __name__ == '__main__':
    main()
