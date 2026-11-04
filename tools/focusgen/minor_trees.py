#!/usr/bin/env python3
"""나머지 13개국의 컨셉 중점 트리 생성 (사양서 16).

사용법 (python -I):
    python -I tools/focusgen/minor_trees.py            # 13개국 조각·국민정신·로컬라이제이션을 쓰고
    python -I tools/focusgen/merge_focus.py --tag LEI   # 태그마다 합치기 (자동 배치)

트리 모양: 시작 중점 1개 -> 갈래 4개. 갈래 = 중점 6~7개 사슬, 4번째 자리는 양자택일 두 개(다음 중점은 둘 중 하나만 있으면 됨).
갈래 마지막 중점은 그 갈래 국민정신을 준다. 보상은 영어 이름으로 theme_effects.py가 정한다.
"economy" 갈래는 공장·기반시설 건설을 더한다 (철도·도로 = 기반시설, 군수/무기 = 군수 공장, 항구·조선 = 조선소, 그 밖 = 민간 공장).
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from theme_effects import theme_of, reward_lines, idea_modifiers, FOCUS_ICON, IDEA_PICTURE  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"

# 공통 경제 갈래 (나라 이름은 {n}/{e})
def economy(n_ko, n_en, first=("광산 개발", "Mining Development")):
    return ("economy", "industry", ("%s 산업" % n_ko, "%s Industry" % n_en), [
        first,
        ("도로망 건설", "Road Network"),
        ("공업 지구", "Industrial District"),
        [("민간 공장 계획", "Civilian Factory Program"), ("군수 공장 계획", "Arms Factory Program")],
        ("철도 연결", "Rail Network Expansion"),
        ("%s 산업화" % n_ko, "%s Industrialisation" % n_en),
    ])

# 태그: (시작 중점 (ko, en), [갈래 ...]). 갈래 = (키, 국민정신 테마, 국민정신 이름 (ko, en), 중점 목록)
TREES = {
    "LEI": (("쌍둥이 여제의 시대", "Age of the Twin Empresses"), [
        ("politics", "politics", ("쌍둥이 여제의 통치", "Rule of the Twin Empresses"), [
            ("선제후 회의", "Electors' Council"), ("마왕의 유산 정리", "Settle the Witch King's Legacy"),
            ("궁정 개혁", "Court Reform"),
            [("여제의 칙령", "Edict of the Empresses"), ("선제후 자치", "Electoral Autonomy")],
            ("왕관의 재건", "Restore the Crown"), ("제국 통합 헌장", "Imperial Unity Charter")]),
        ("arts", "research", ("아츠의 정점", "Pinnacle of Arts"), [
            ("아츠 학원", "Arts Academy of Leithanien"), ("음악 아츠 연구", "Musical Arts Research"),
            ("오페라 극장", "Opera House Festival"),
            [("전투 아츠 연구", "Combat Arts Research"), ("생활 아츠 공학", "Civilian Arts Engineering")],
            ("아츠 증폭기", "Arts Amplifier Research"), ("아츠의 정점", "Pinnacle of Arts Studies")]),
        ("military", "doctrine", ("라이타니엔 정예군", "Leithanian Elite Army"), [
            ("라이타니엔 근위대", "Leithanian Guard Regiments"), ("아츠 포병", "Arts Artillery"),
            ("산악 요새선", "Mountain Fortress Line"),
            [("기동전 교리", "Mobile Warfare Doctrine"), ("수비 교리", "Defensive Doctrine")],
            ("장교 학교", "Officer School"), ("정예 술사단", "Elite Caster Corps")]),
        economy("라이타니엔", "Leithanian"),
    ]),
    "IBE": (("대침묵 이후", "After the Great Silence"), [
        ("politics", "intel", ("심판소의 눈", "Eyes of the Inquisition"), [
            ("심판소 재편", "Inquisition Court Reform"), ("왕실 회의", "Crown Council"),
            ("성교회 협약", "Church Accord"),
            [("심판관의 통치", "Rule of the Inquisitors"), ("왕실의 부활", "Revival of the Crown")],
            ("해안 도시 행정", "Coastal City Administration"), ("이베리아 헌장", "Iberian Charter")]),
        ("sea", "navy", ("바다를 지키는 자", "Guardians of the Coast"), [
            ("해안 감시", "Coastal Watch"), ("등대 재건", "Lighthouse Restoration on the Coast"),
            ("바다의 위협 연구", "Study of the Sea Threat"),
            [("해안 요새", "Coastal Fortress Line"), ("함대 재건", "Fleet Reconstruction")],
            ("심해 대비 계획", "Deep Sea Defence Plan"), ("이베리아 해군", "Iberian Navy")]),
        ("military", "doctrine", ("심판관 정예대", "Elite Inquisitor Corps"), [
            ("심판관 근위대", "Inquisitor Guard"), ("총검술 훈련", "Bayonet Drill"),
            ("산악 보병", "Mountain Infantry Regiments"),
            [("기동전 교리", "Mobile Warfare Doctrine"), ("참호 방어", "Trench Defence")],
            ("포병 재건", "Artillery Rebuild"), ("정예 심판관", "Elite Inquisitor Training")]),
        economy("이베리아", "Iberian", ("항구 재건", "Harbour Reconstruction")),
    ]),
    "LAT": (("교황청의 축복", "Holy See Blessing"), [
        ("politics", "propaganda", ("성도의 평화", "Peace of the Holy City"), [
            ("공증인 사무소", "Notarial Hall Office"), ("교황청 회의", "Papal Council"),
            ("추기경단", "College of Cardinals"),
            [("교황의 권위", "Papal Authority"), ("추기경단의 합의", "Cardinals' Accord")],
            ("순례자 환영", "Welcome the Pilgrims"), ("라테라노 평화 협정", "Laterano Peace Accord")]),
        ("firearms", "infantry_weapons", ("라테라노 총기", "Laterano Firearms"), [
            ("총기 공방", "Firearm Workshops"), ("성가 탄약", "Hymn Ammunition"),
            ("성당 포대", "Cathedral Artillery"),
            [("저격 교리", "Marksman Tactics"), ("화력 집중 교리", "Firepower Doctrine")],
            ("총기 수출", "Firearm Exports"), ("산크타 총사대", "Sankta Musketeer Corps")]),
        ("military", "air", ("하늘의 사도", "Apostles of the Sky"), [
            ("라테라노 근위대", "Laterano Guard"), ("수호천사 기동대", "Guardian Rapid Response Force"),
            ("성도 성벽", "Holy City Walls"),
            [("공중 순찰", "Air Patrol"), ("지상 순찰", "Ground Patrol Watchtowers")],
            ("장교 학교", "Officer School"), ("하늘의 사도", "Apostles of the Sky Wing")]),
        economy("라테라노", "Laterano", ("순례 경제", "Pilgrimage Trade")),
    ]),
    "KAZ": (("기사의 나라", "Land of Knights"), [
        ("politics", "trade", ("상업 연합회", "The Commercial Union"), [
            ("상업 연합회 이사회", "Commercial Union Council"), ("기사 협회", "Knights' Association"),
            ("언론 장악", "Media Broadcast Control"),
            [("연합회의 지배", "Rule of the Commercial Union"), ("기사의 귀환", "Return of the Knights")],
            ("감염자 기사의 권리", "Infected Knights Rights"), ("새 카시미어 헌장", "New Kazimierz Charter")]),
        ("knights", "armor", ("카시미어 기사단", "Knightly Orders of Kazimierz"), [
            ("메이저 기사 경기", "Major Tournament"), ("기사 훈련소", "Knight Training Grounds"),
            ("기갑 기사단", "Armoured Knight Orders"),
            [("돌격 기병", "Cavalry Charge"), ("중장 기사", "Heavy Armour Knights")],
            ("기동전 교리", "Mobile Warfare Doctrine"), ("무광 기사단", "Elite Lightless Knights")]),
        ("military", "manpower", ("카시미어 상비군", "Kazimierz Standing Army"), [
            ("용병 계약", "Mercenary Contracts"), ("국경 요새", "Border Fortresses"),
            ("포병 중대", "Artillery Companies"),
            [("공격 교리", "Offensive Doctrine"), ("방어 교리", "Defensive Doctrine")],
            ("장비 현대화", "Equipment Modernisation"), ("카시미어 상비군", "Kazimierz Standing Army Regiments")]),
        economy("카시미어", "Kazimierz", ("상업 도시", "Merchant Cities Trade")),
    ]),
    "HIG": (("극동 조정 회의", "Far East Court Assembly"), [
        ("politics", "propaganda", ("무사의 정신", "Spirit of the Warrior"), [
            ("조정 개혁", "Imperial Court Reform"), ("다이묘 회의", "Daimyo Council Reform"),
            ("국경 검문", "Border Inspection Watchposts"),
            [("쇄국령", "Isolation Edict"), ("개항", "Open the Harbours")],
            ("무사도", "Bushido Spirit"), ("극동 헌장", "Far East Charter")]),
        ("navy", "navy", ("극동 연합 함대", "Far East Combined Fleet"), [
            ("어항 정비", "Fishing Port Upgrade"), ("연안 함대", "Coastal Fleet"),
            ("해군 학교", "Naval Academy"),
            [("순양함 함대", "Cruiser Fleet"), ("잠수함 함대", "Submarine Fleet")],
            ("해상 교역로", "Sea Trade Lanes"), ("연합 함대", "Combined Fleet")]),
        ("military", "doctrine", ("극동 정예군", "Far East Elite Army"), [
            ("무사단", "Samurai Regiments"), ("검술 훈련", "Swordsmanship Drill"),
            ("산성 축조", "Mountain Fortresses"),
            [("기습 전술", "Raid Tactics"), ("수비 전술", "Defensive Tactics")],
            ("포병 대대", "Artillery Battalions"), ("그림자 정예대", "Elite Shadow Corps")]),
        economy("극동", "Far East", ("쌀 수확", "Rice Harvest")),
    ]),
    "COL": (("자유의 나라", "Land of Liberty"), [
        ("politics", "politics", ("컬럼비아 헌법", "Columbian Constitution"), [
            ("의회 개회", "Congress Session"), ("대통령 선거", "Presidential Election"),
            ("서부 황야 정착", "Settle the Western Wilderness"),
            [("연방 강화", "Strengthen the Federation"), ("주정부 자치", "States' Autonomy")],
            ("언론의 자유", "Free Press Broadcast"), ("컬럼비아 헌법", "Columbian Constitution Charter")]),
        ("research", "research", ("과학 강국", "Scientific Superpower"), [
            ("라인 생명 협력", "Rhine Lab Partnership"), ("원석 공학", "Originium Engineering"),
            ("대학 연구소", "University Institutes"),
            [("무기 연구", "Weapons Research"), ("산업 연구", "Industrial Research")],
            ("레이더 연구", "Radar Research"), ("과학 강국", "Scientific Superpower Programme")]),
        ("military", "air", ("컬럼비아 공군", "Columbian Air Force"), [
            ("공군 창설", "Air Force Founding"), ("전투기 계획", "Fighter Programme"),
            ("폭격기 계획", "Bomber Programme"),
            [("기계화 보병", "Mechanised Infantry"), ("기갑 사단", "Armoured Divisions")],
            ("기동전 교리", "Mobile Warfare Doctrine"), ("컬럼비아 육군 사령부", "Columbian Army Command")]),
        economy("컬럼비아", "Columbian", ("석유 산업", "Oil Industry")),
    ]),
    "SAR": (("파디샤의 땅", "Land of the Padishah"), [
        ("politics", "politics", ("사르곤 통일", "Unified Sargon"), [
            ("왕자들의 회의", "Council of Princes"), ("조공 체계", "Tribute System"),
            ("부족 화합", "Tribal Accord"),
            [("파디샤 중앙집권", "Padishah Centralisation"), ("영주 자치", "Lords' Autonomy")],
            ("사막 행정", "Desert Administration"), ("사르곤 통일", "Unify Sargon")]),
        ("military", "mobile", ("사막의 전사들", "Warriors of the Desert"), [
            ("사막 전사", "Desert Warriors"), ("낙타 기병", "Camel Cavalry"),
            ("정글 전투 훈련", "Jungle Warfare Training"),
            [("기습 전술", "Raid Tactics"), ("요새 방어", "Fortress Defence")],
            ("활과 창 무기고", "Bow and Spear Arsenal"), ("파디샤 근위대", "Padishah Guard")]),
        ("trade", "trade", ("황금의 나라", "Golden Kingdom"), [
            ("황금 무역", "Gold Trade"), ("대상단 교역", "Caravan Trade"),
            ("오아시스 시장", "Oasis Markets"),
            [("교역 독점", "Trade Monopoly"), ("자유 교역", "Free Trade")],
            ("사르곤 국고", "Sargon Treasury"), ("황금의 나라", "Golden Kingdom Economy")]),
        economy("사르곤", "Sargon"),
    ]),
    "MIN": (("도시국가 연맹", "League of City States"), [
        ("politics", "diplomacy", ("미노스 동맹", "Minoan League"), [
            ("아고라 회의", "Agora Assembly"), ("철학자 회의", "Philosophers' Council"),
            ("신전 의례", "Temple Rites"),
            [("민주 정체", "Democratic Polis"), ("원로 정체", "Rule of the Elders")],
            ("동맹 맹약", "League Pact"), ("미노스 헌장", "Minos Charter")]),
        ("navy", "navy", ("미노스 대함대", "Minoan Grand Fleet"), [
            ("항구 정비", "Harbour Works"), ("갤리 함대", "Galley Fleet"),
            ("해군 학교", "Naval Academy"),
            [("상선 함대", "Merchant Fleet"), ("전투 함대", "Battle Fleet")],
            ("해상 패권", "Sea Supremacy"), ("미노스 대함대", "Minoan Grand Fleet")]),
        ("culture", "research", ("지혜의 도시", "City of Knowledge"), [
            ("철학 학교", "School of Philosophy"), ("수학 연구", "Mathematics Studies"),
            ("천문대", "Observatory"),
            [("의학 연구", "Medical Studies"), ("공학 연구", "Engineering Studies")],
            ("대도서관", "Great Library"), ("지혜의 도시", "City of Knowledge Research")]),
        economy("미노스", "Minoan", ("올리브 농장", "Olive Farms")),
    ]),
    "BOL": (("끝나지 않는 내전", "The Endless Civil War"), [
        ("politics", "diplomacy", ("볼리바르 공화국", "Bolivar Republic"), [
            ("휴전 협상", "Ceasefire Talks"), ("군벌 통합", "Unite the Warlords"),
            ("국민 화해", "National Reconciliation"),
            [("컬럼비아와의 동맹", "Columbian Alliance"), ("빅토리아와의 동맹", "Victorian Alliance")],
            ("새 정부", "New Government"), ("볼리바르 공화국", "Bolivar Republic Charter")]),
        ("military", "manpower", ("볼리바르 정규군", "Bolivar Regular Army"), [
            ("민병대 소집", "Militia Levy"), ("게릴라전 교리", "Guerrilla Doctrine"),
            ("정글 요새", "Jungle Fortifications"),
            [("외국 용병", "Foreign Mercenaries"), ("국민군", "National Army")],
            ("무기 밀수", "Arms Smuggling"), ("볼리바르 정규군", "Bolivar Regular Army Regiments")]),
        ("recovery", "medical", ("평화의 시대", "Era of Peace"), [
            ("난민 구호", "Refugee Relief"), ("병원 재건", "Hospital Rebuild"),
            ("식량 배급", "Grain Rationing"),
            [("교육 재건", "Education Reform"), ("주택 재건", "Housing Rebuild")],
            ("전쟁 고아 쉼터", "War Orphan Shelters"), ("평화의 시대", "Era of Peace Relief")]),
        economy("볼리바르", "Bolivar", ("커피 농장", "Coffee Farms")),
    ]),
    "SIR": (("늑대의 땅", "Land of Wolves"), [
        ("politics", "politics", ("시라쿠사 헌장", "Siracusan Charter"), [
            ("패밀리 회담", "Family Summit"), ("늑대 군주의 유산", "Wolf Lord's Legacy"),
            ("법원 개혁", "Court Reform"),
            [("패밀리의 통치", "Rule of the Families"), ("법의 통치", "Rule of Law")],
            ("시민 질서 경찰", "Public Order Police"), ("시라쿠사 헌장", "Siracusa Charter")]),
        ("families", "trade", ("황금 늑대", "The Golden Wolf"), [
            ("밀수 단속", "Smuggler Crackdown"), ("카지노 교역", "Casino Trade"),
            ("패밀리 은행", "Family Bank"),
            [("패밀리 사업", "Family Businesses"), ("합법 기업", "Legal Companies")],
            ("수익 장부", "Profit Ledger"), ("황금 늑대 금고", "Golden Wolf Treasury")]),
        ("military", "doctrine", ("시라쿠사 군", "Siracusan Army"), [
            ("패밀리 경호대", "Family Bodyguard Regiments"), ("시가전 전술", "Urban Warfare Tactics"),
            ("항구 방어", "Harbour Defence"),
            [("기동 타격대", "Rapid Strike Squads"), ("요새 도시", "Fortress Cities")],
            ("무기 공방", "Arms Workshops"), ("시라쿠사 군 사령부", "Siracusan Army Command")]),
        economy("시라쿠사", "Siracusan"),
    ]),
    "SAM": (("숲의 수호자", "Guardians of the Forest"), [
        ("politics", "propaganda", ("사미의 결속", "Unity of Sami"), [
            ("무녀 회의", "Shaman Council"), ("성스러운 숲의 의례", "Sacred Forest Rites"),
            ("부족 연합", "Sami Tribal Federation"),
            [("숲의 고립", "Isolation of the Forest"), ("바깥과의 접촉", "Open Contact")],
            ("사미의 맹세", "Oath of Sami"), ("사미의 결속", "Sami Unity")]),
        ("military", "doctrine", ("정령 전사", "Spirit Warriors"), [
            ("설원 사냥꾼", "Snowfield Hunters"), ("스키 기습대", "Ski Raid Squads"),
            ("숲 매복 전술", "Forest Ambush Tactics"),
            [("설원 요새", "Snow Fortresses"), ("기동 사냥꾼", "Mobile Hunters")],
            ("활 장인", "Bow Smiths"), ("정령 전사단", "Elite Spirit Warriors")]),
        ("arts", "research", ("사미의 아츠", "Arts of Sami"), [
            ("무녀의 지혜", "Shaman Wisdom Studies"), ("정령 아츠 연구", "Spirit Arts Research"),
            ("약초 의술", "Herbal Medicine"),
            [("얼음 아츠", "Ice Arts Research"), ("숲의 아츠", "Forest Arts Research")],
            ("고대 비석", "Ancient Runestones"), ("사미 아츠의 정수", "Sami Arts Mastery Research")]),
        economy("사미", "Sami", ("목재 산업", "Timber Industry")),
    ]),
    "KJE": (("설산의 나라", "Kingdom of the Snow Mountains"), [
        ("politics", "propaganda", ("쉐라그드르의 가호", "Grace of Kjeragandr"), [
            ("성녀의 축복", "Blessing of the Saintess"), ("장로 회의", "Elders' Council"),
            ("쉐라그드르 신앙", "Kjeragandr Faith"),
            [("칼란 무역의 집권", "Karlan Trade Rule"), ("귀족 가문의 집권", "Noble Houses Rule")],
            ("세 가문의 화해", "Reconciliation of the Three Houses"), ("쉐라그 헌장", "Kjerag Charter")]),
        ("military", "fort", ("설산의 수호자", "Guardians of the Mountains"), [
            ("산악 보병", "Mountain Infantry Regiments"), ("설산 요새", "Snow Mountain Fortresses"),
            ("스키 기동대", "Ski Mobile Troops"),
            [("산악전 교리", "Mountain Warfare Doctrine"), ("고지 방어", "Highland Defence")],
            ("사격 훈련", "Marksman Training"), ("설산 정예대", "Elite Mountain Guard")]),
        ("karlan", "trade", ("칼란 무역", "Karlan Trade"), [
            ("칼란 무역 회사", "Karlan Trade Company"), ("은 광산", "Silver Mines"),
            ("외국 투자", "Foreign Investment Fund"),
            [("기술 수입", "Technology Imports"), ("자립 공업", "Self-Sufficient Industry")],
            ("쉐라그 은행", "Kjerag Bank"), ("실버애쉬의 비전", "Silverash's Industrial Vision")]),
        economy("쉐라그", "Kjerag", ("목재 산업", "Timber Industry")),
    ]),
    "RIM": (("원석 광산 국가", "The Mining Nation"), [
        ("politics", "politics", ("새로운 터전", "A New Homeland"), [
            ("회사 이사회", "Company Board"), ("이주민 정책", "Refugee Policy"),
            ("감염자 권리", "Infected Rights"),
            [("회사 통치", "Corporate Rule"), ("노동자 자치", "Workers' Self-Government")],
            ("정착민 의회", "Settlers' Council"), ("림 빌리튼 헌장", "Rim Billiton Charter")]),
        ("mining", "industry", ("광산 대국", "Mining Superpower"), [
            ("광석 채굴", "Ore Mining"), ("원석 정제소", "Ore Refinery"),
            ("광산 철도", "Mining Railway"),
            [("자동화 광산", "Automated Mines"), ("노동 확대", "Labour Expansion")],
            ("광석 수출", "Ore Exports"), ("광산 대국", "Mining Superpower")]),
        ("security", "fort", ("림 빌리튼 방위군", "Rim Billiton Defence Force"), [
            ("회사 경비대", "Company Security Force"), ("광산 방어선", "Mine Defence Line"),
            ("용병 고용", "Mercenary Hire"),
            [("기동 경비대", "Rapid Security Squads"), ("요새화된 광산", "Fortified Mines")],
            ("장비 보급", "Equipment Supply"), ("림 빌리튼 방위군", "Rim Billiton Defence Force")]),
        ("medical", "medical", ("광석병과의 싸움", "Fight Against Oripathy"), [
            ("광석병 연구", "Oripathy Research"), ("의료 센터", "Medical Centres"),
            ("난민 정착촌", "Refugee Settlements"),
            [("억제제 생산", "Suppressant Production"), ("격리 구역", "Quarantine Zones")],
            ("원석 공학", "Originium Engineering"), ("새로운 터전", "New Homeland Relief")]),
    ]),
}

HEADER = """focus_tree = {
	id = TU_%(TAG)s_focus
	continuous_focus_position = { x = 50 y = 1200 }

	country = {
		factor = 0
		modifier = {
			add = 10
			original_tag = %(TAG)s
		}
	}

	reset_on_civilwar = no

	initial_show_position = {
		focus = TU_%(TAG)s_root
	}
"""


def slug(en):
    s = re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")
    return s[:40].rstrip("_")


def build_kind(theme, en):
    e = en.lower()
    if re.search(r"rail|road", e):
        return "TU_build_infrastructure"
    if theme in ("infantry_weapons", "artillery") or "arms factory" in e:
        return "TU_build_mil_factory"
    return "TU_build_civ_factory"


def focus(fid, en, prereq, me=None, cost=10, extra=(), industry=False, econ=False):
    theme = theme_of(en)
    rw = list(extra)
    if econ:
        rw.append("%s = yes" % build_kind(theme, en))
    rw += reward_lines(theme, fid, cost)
    pre = "".join("\t\tprerequisite = { %s }\n" % " ".join("focus = %s" % x for x in g) for g in prereq)
    mex = "\t\tmutually_exclusive = { focus = %s }\n" % me if me else ""
    flt = "FOCUS_FILTER_INDUSTRY" if (industry or econ) else "FOCUS_FILTER_POLITICAL"
    return """	focus = {
		id = %s
		icon = %s
%s%s		x = 0
		y = 0
		cost = %d

		search_filters = { %s }

		ai_will_do = {
			base = 1
		}

		completion_reward = {
%s
		}
	}

""" % (fid, FOCUS_ICON.get(theme, FOCUS_ICON["politics"]), pre, mex, cost, flt,
       "\n".join("\t\t\t" + l for l in rw))


def build_tag(tag, spec):
    (root_ko, root_en), branches = spec
    ko, en = [], []
    parts = []
    root = "TU_%s_root" % tag
    parts.append(focus(root, root_en, [], cost=5, extra=["add_political_power = 50"]))
    ko += [(root, root_ko), (root + "_desc", "")]
    en += [(root, root_en), (root + "_desc", "")]
    ideas = []
    for key, idea_theme, (iko, ien), items in branches:
        prev = [root]
        econ = key == "economy"
        for idx, it in enumerate(items):
            last = idx == len(items) - 1
            if isinstance(it, list):
                ids = ["TU_%s_%s_%s" % (tag, key, slug(x[1])) for x in it]
                for j, (k, e) in enumerate(it):
                    parts.append(focus(ids[j], e, [prev], me=ids[1 - j], econ=econ))
                    ko += [(ids[j], k), (ids[j] + "_desc", "")]
                    en += [(ids[j], e), (ids[j] + "_desc", "")]
                prev = ids
                continue
            k, e = it
            fid = "TU_%s_%s_%s" % (tag, key, slug(e))
            extra = []
            if last:
                iid = "TU_%s_idea_%s" % (tag, key)
                extra.append("add_ideas = %s" % iid)
                ideas.append((iid, idea_theme, iko, ien))
            parts.append(focus(fid, e, [prev], econ=econ, extra=extra))
            ko += [(fid, k), (fid + "_desc", "")]
            en += [(fid, e), (fid + "_desc", "")]
            prev = [fid]
    folder = HERE / tag.lower()
    folder.mkdir(exist_ok=True)
    (folder / "_header.txt").write_text(HEADER % {"TAG": tag}, encoding="utf-8")
    (folder / "p1_all.txt").write_text("\t#### %s CONCEPT TREE (generated by tools/focusgen/minor_trees.py) ####\n\n" % tag
                                       + "".join(parts).rstrip("\n") + "\n", encoding="utf-8")
    # ideas
    blocks = []
    for iid, th, iko, ien in ideas:
        mods = "\n".join("\t\t\t\t%s = %s" % kv for kv in idea_modifiers(th).items())
        blocks.append("""		%s = {
			picture = %s

			allowed = {
				original_tag = %s
			}

			modifier = {
%s
			}
		}
""" % (iid, IDEA_PICTURE.get(th, "generic_central_management"), tag, mods))
        ko += [(iid, iko), (iid + "_desc", "")]
        en += [(iid, ien), (iid + "_desc", "")]
    (MOD / "common" / "ideas" / ("tu_%s_concept_ideas.txt" % tag.lower())).write_text(
        "ideas = {\n\n\tcountry = {\n\n" + "\n".join(blocks) + "\t}\n}\n", encoding="utf-8")
    ko.append(("TU_%s_focus" % tag, "%s 중점" % root_ko))
    en.append(("TU_%s_focus" % tag, "%s Focus" % root_en))
    for lang, items in (("korean", ko), ("english", en)):
        lines = ["l_%s:" % lang] + [' %s:0 "%s"' % (k, v.replace('"', '\\"')) for k, v in items]
        (MOD / "localisation" / lang / ("tu_%s_concept_l_%s.yml" % (tag.lower(), lang))).write_bytes(
            ("\n".join(lines) + "\n").encode("utf-8-sig"))
    return len([p for p in parts])


def main():
    total = 0
    for tag, spec in TREES.items():
        if (HERE / "content" / ("%s.py" % tag.lower())).exists():
            print("%s skipped (tools/focusgen/content/%s.py owns this tree)" % (tag, tag.lower()))
            continue
        n = build_tag(tag, spec)
        total += n
        print("%s focuses=%d" % (tag, n))
    print("MINOR_TREES ok tags=%d focuses=%d" % (len(TREES), total))


if __name__ == "__main__":
    main()
