"""컬렉션 ZXA 에만 있는 원문(NDS 일본판과 다른 메시지)의 번역 → zx/zxa_coll_ko.json {원문: 번역}.
python tools/zxa_coll_ko.py  (입력: _work/zxa_new_split.json — 컬렉션 원문, 가장 비슷한 NDS 원문과 그 번역)
- 'same'(제어·줄 골격이 같음): 표기만 바뀐 것은 NDS 번역 그대로, 낱말이 바뀐 것은 EDIT_S 로 고침.
- 'diff'(골격이 바뀜): EDIT_D 로 고침. 둘 다 아래 함수 하나가 (NDS 번역) → 새 번역을 만든다.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = '\n'
P = '{p}' + N


def rep(*args):
    """rep(찾을 말, 바꿀 말, 찾을 말, 바꿀 말, …)"""
    pairs = list(zip(args[0::2], args[1::2]))
    assert len(args) % 2 == 0

    def f(ko):
        for a, b in pairs:
            assert a in ko, (a, ko[:80])
            ko = ko.replace(a, b)
        return ko
    return f


def full(text):
    return lambda ko: text


def add_p(ko):            # 컬렉션이 메시지 끝에 쪽 넘김을 붙여 둠
    return ko + P


def drop_last_page(ko):
    return ko[:ko.rindex('{p}')]


EDIT_S = {
    6: lambda ko: ko + N,                # 원문 끝 줄바꿈(NDS 번역이 빠뜨림)
    8: rep('공격하자! 다만\n너무 다가가면 버닝 애로를', '공격하자!\n다만 너무 다가가면 파이어 애로를'),
    9: full('크게 퍼지는 로즈 스팅어나\n로즈 스파크를 피하려면\n늘 로즈파크의 뒤로\n돌아 들어가듯 움직이자. 벽에서\n'
            '대시 점프로 뛰어넘자.\n기가 레이저는 화면 아래에 있으면\n맞지 않는다!'),
    11: rep('무기 컨테이너의', '옵션의', '무기 컨테이너는', '옵션은'),
    20: full('독일어 LR 버튼용'),
    30: rep('그리고 비기너 모드에선', '캐주얼 시나리오 모드에선'),
    31: rep('아래 화면 약도에서\n가고 싶은 곳을 터치하거나', '화면 약도에서 가고 싶은 곳을\n셀렉트 버튼으로 터치하거나'),
    51: rep('그리고 비기너 모드에선', '캐주얼 시나리오 모드에선'),
    52: rep('아래 화면의 아이콘을\n터치해 봐!', '서브 화면의 아이콘을\n셀렉트 버튼으로 터치해 봐!'),
    53: rep('한 번 더 아래 화면 아이콘을\n터치해!', '한 번 더 서브 화면의\n아이콘을 터치해!'),
    54: rep('아래 화면의 아이콘을\n터치해 봐!', '서브 화면의 아이콘을\n셀렉트 버튼으로 터치해 봐!'),
    55: rep('버스터 샷 버튼을', '레이저 샷 버튼을'),
    56: rep('아래 화면 오른쪽 아래에 있는', '서브 화면 오른쪽 아래에 있는',
            '아래 화면이 레이더 스코프로', '서브 화면이 레이더 스코프로',
            '아래 화면에 비친\n적 마크를 직접 터치해서\n공격도 할 수 있대…',
            '서브 화면에 비친 적 마크를\n셀렉트 버튼으로 터치해서\n공격도 할 수 있대…'),
    57: rep('테티스한테는 아래 화면에', '테티스한테는 서브 화면에'),
    58: rep('테티스한테는 아래 화면에', '테티스한테는 서브 화면에'),
    59: rep('아래 화면에서 적 데이터를', '서브 화면에서 적 데이터를'),
    60: full('{F2:02}{F3:4b}{F8:45}내 가방이\n어디 갔을까{p}\n앗! 그거 혹시\n내 가방이야?{p}\n'
             '그 안엔 내 소중한\n보물이 잔뜩\n들어 있단 말이야!'),
    61: full('{F2:02}{F3:4b}{F8:45}고마워!{p}\n찾아 준 패트릭 씨한테\n뭔가 답례를\n해야 할 텐데…{p}\n'
             '어제 만화를 사 버려서\n가진 E크리스탈이\n하나도 없고…{p}\n그래!\nE크리스탈 대신\n'
             '이 디스크를 전해 줘{p}\n내가 제일 좋아하는 히어로의\n만화가 수록된\n스페셜 디스크야!'),
    62: full('{F2:02}{F3:4b}{F8:45}그럼 패트릭 씨한테\n안부 전해 줘!'),
    80: rep('회수해 왔어요!', '포획해서 돌아왔어요!'),
    81: rep('설계도를 가져와\n줬구나\n이걸로 바를 만들 수 있어!', '고마워\n이걸로 레플리로이드 전용\n바를 만들 수 있어!'),
    82: rep('야, 알아?', '있잖아, 알아?'),
    85: full('{F2:02}{F3:4b}{F8:45}전설의 히어로 굿즈?{p}\n아아, 그거라면 요전에\n돈이 궁해서\n팔아 버렸어{p}\n'
             '헌터 티나가\n멋진 남자 사진을\n보고 싶다고 해서…{p}\n놓고 싶진 않았지만\n티나가 너무\n갖고 싶어 했거든'),
    86: rep('컨트롤 센터', '컨트롤 타워'),
    89: rep('레기온즈에서', '레기온즈 정부에서'),
    90: rep('레기온즈 본부에서', '레기온즈 정부에서'),
    91: rep('나머진 그 의뢰서를', '나머진 그 의뢰서를 들고'),
    92: rep('레기온즈 본부에서도', '레기온즈 정부에서도'),
    93: rep('컨트롤 센터에', '컨트롤 타워에'),
    95: rep('쥐 모양 메카니로이드를', '쥐 모양 졸개를'),
    107: lambda ko: ko + '.',
    108: full('{F3:05}{F8:5d}전송할 곳을\n골라 주세요'),
}
# 'same' 에서 위에 없는 번호는 NDS 번역 그대로(표기 차이: 한자↔가나, 문장부호, 1인칭 등 — 한국어에선 같음)

EDIT_D = {
    8: full('셀렉트 버튼…버스터 에디트'),
    19: full('서브 화면에서\n편집해 주세요.'),
    27: drop_last_page,
    28: rep('그리고 버스터 샷은\n아래 화면에서 탄의 궤도를', '그리고 버스터 샷은\n탄의 궤도를',
            '우선 서브 화면 상태 화면에서\nSELECT 버튼을 누르면\n아래 화면을 조작할 수 있어',
            '우선 서브 화면 상태 화면에서\n셀렉트 버튼을 누르면 조작할 수 있어',
            '그다음 아래 화면 칸을\n터치하거나 ✚버튼으로', '그다음 화면 칸을 셀렉트 버튼으로\n터치하거나 ✚버튼으로'),
    29: rep('{F2:03}{F9:8202}{F3:19}{F8:19}하지만', '{F9:8202}하지만'),
    30: rep('{F2:03}{F9:4b04}{F3:08}{F8:02}', '{F2:03}{F9:4b04}{F3:08}{F8:01}'),
    31: rep('{F2:02}{F6:01}', '{F6:01}'),
    32: lambda ko: rep('{F2:03}', '{F2:02}')(ko) + N,   # 원문 끝 줄바꿈도
    33: rep('{F2:02}{F6:01}', '{F6:01}'),
    34: drop_last_page,
    35: lambda ko: ko[ko.index('…날 구하러'):].join(['{F2:02}{F3:74}{F8:1d}', '']),
}
# 'diff' 에서 위에 없는 번호: 끝에 쪽 넘김만 붙은 것(add_p)


def skel(s):
    return re.findall(r'\{(?!J[0-9A-F]{3}\})[^}]*\}|\n', s)     # {J218} 같은 한자 토큰은 글자라 뺀다


def split():
    """컬렉션 ZXA 원문 중 NDS 원고에 같은 원문이 없는 메시지(일본어 포함) → 가장 비슷한 NDS 원문·번역과 짝지어
    {'same': 제어·줄 골격이 같은 것, 'diff': 다른 것}. 순서는 파일(NDS 원문 덤프 순) → 메시지 순, 같은 원문은 첫 위치 하나."""
    import difflib
    import sys
    nds = os.path.join(os.path.dirname(ROOT), 'Rockman ZX, Advent')
    sys.path.insert(0, os.path.join(nds, 'tools'))
    import build_zx as bz
    import zxtext
    src = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'ZXA', 'DATA')
    J = json.load(open(os.path.join(nds, 'data', 'zxa_jp.json'), encoding='utf-8'))
    tr = bz.load_translations('zxa', J)
    by_src = {}
    for f, v in J.items():
        for i, m in enumerate(v['msgs']):
            t = tr.get((f[:-4], i))
            if t is not None:
                by_src.setdefault(m['s'], t)
    cm = zxtext.prep(zxtext.load_charmap('zxa'), True)
    uniq = {}
    for f in J:
        if f == 'm_mg_ds_jp.bin':
            continue
        b = open(os.path.join(src, f), 'rb').read()
        A, base, offs = zxtext.parse(b)
        i, k = base, 0
        while i < A + 4:
            s, i, term = zxtext.decode_msg(b, i, cm)
            if s and s not in by_src and re.search(r'[ぁ-んァ-ヶ一-龯]', s):
                uniq.setdefault(s, []).append([f, k])
            k += 1
    srcs = list(by_src)
    out = []
    for s, locs in uniq.items():
        cands = [m['s'] for m in J[locs[0][0]]['msgs'] if m['s'] in by_src] or srcs
        best = max(cands, key=lambda x: difflib.SequenceMatcher(None, s, x, autojunk=False).ratio())
        out.append(dict(locs=locs, s=s, ref=best, ko=by_src[best]))
    return {'same': [o for o in out if skel(o['s']) == skel(o['ref'])],
            'diff': [o for o in out if skel(o['s']) != skel(o['ref'])]}


def main():
    D = split()
    old = os.path.join(ROOT, '_work', 'zxa_new_split.json')
    if os.path.exists(old):     # 처음 만들 때 쓴 비교 자료와 순서·원문이 같아야 EDIT_S/EDIT_D 번호가 맞는다
        O = json.load(open(old, encoding='utf-8'))
        for key in ('same', 'diff'):
            assert [o['s'] for o in D[key]] == [o['s'] for o in O[key]], ('비교 자료 순서가 다름', key)
    out = {}
    for k, o in enumerate(D['same']):
        out[o['s']] = EDIT_S.get(k, lambda ko: ko)(o['ko'])
    for k, o in enumerate(D['diff']):
        ko = o['ko']
        if k in EDIT_D:
            ko = EDIT_D[k](ko)
        else:
            assert o['s'].endswith(P) and not o['ref'].endswith(P), ('끝 쪽 넘김이 아닌 골격 변화', k)
            assert o['s'][:-len(P)] == o['ref'] or skel(o['s'][:-len(P)]) == skel(o['ref']), k
            ko = add_p(ko)
        out[o['s']] = ko
    bad = [(s[:30], t[:30]) for s, t in out.items() if skel(s) != skel(t)]
    assert not bad, ('골격 불일치', bad)
    os.makedirs(os.path.join(ROOT, 'zx'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'zx', 'zxa_coll_ko.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('컬렉션 전용 ZXA 번역', len(out))


if __name__ == '__main__':
    main()
