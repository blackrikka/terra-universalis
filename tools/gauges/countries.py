"""디시전 탭에 들어갈 나라별 수치 목록 (build_gauges.py, focusgen/content_lib.py 가 읽는다).

나라: (태그, [수치…]) / 어느 탭에 놓을지는 아래 TABS 에 적는다 (그 수치를 가장 많이 다루는 탭)
수치: G(변수, 이름 ko, 이름 en, 색, tip=(설명 ko, en), …)
  색: gold(보통) green(좋음) red(나쁨) blue(중립) orange(손상) teal(심해, 짙은 청록)
  kind="number": 막대 없이 숫자만 / max=: clamp_variable 이 없을 때 최댓값 / cap=: 상한이 변수일 때
  value=(ko, en): 값 글자를 바꿀 때. {v} 자리에 변수값이 들어간다
  full=True: 작은 칸 수치도 한 줄 전체를 쓴다
  layers=[(색, 개수 변수)…]: 뒤쪽 칸부터 그 개수만큼 다른 색으로 덮는다 (값이 칸 수인 수치만)
설명의 수치·조건은 기존 디시전 분류 설명에 적힌 것만 옮겼다. 규칙이 바뀌면 여기도 고칠 것.
§Y…§! 노랑, §G…§! 초록, §R…§! 빨강, §g…§! 회색
"""


def G(var, ko, en, color="gold", **kw):
    return dict(var=var, ko=ko, en=en, color=color, **kw)


COUNTRIES = [
    ("BOL", [
        G("TU_BOL_control", "정부 장악력", "Government Control", "green",
          tip=("정부가 실제로 다스리는 땅과 사람들입니다. §Y100§!에 이르면 내전이 끝납니다.",
               "The land and people the government truly holds. At §Y100§! the civil war ends.")),
        G("TU_BOL_weariness", "전쟁 피로", "War Weariness", "red",
          tip=("내전이 이어지는 동안 매달 오릅니다. 이제 사람들은 누가 이기든 상관없다고 말합니다.",
               "Rises every month the civil war drags on. People now say they no longer care who wins.")),
        G("TU_BOL_victoria", "빅토리아 의존", "Victorian Dependence",
          tip=("빅토리아의 원조에 기댄 만큼 쌓입니다. §Y60§!을 넘으면 후원국이 요구를 해 옵니다.",
               "Grows with every Victorian aid package. Above §Y60§! the patron starts making demands.")),
        G("TU_BOL_columbia", "컬럼비아 의존", "Columbian Dependence", "blue",
          tip=("컬럼비아의 원조에 기댄 만큼 쌓입니다. §Y60§!을 넘으면 후원국이 요구를 해 옵니다.",
               "Grows with every Columbian aid package. Above §Y60§! the patron starts making demands.")),
    ]),
    ("COL", [
        G("TU_COL_science", "과학 역량", "Scientific Capacity", "green",
          tip=("국가 연구 프로젝트와 행정이 쌓아 올린 과학의 힘입니다.",
               "The scientific strength built up by national research projects and the administration.")),
    ]),
    ("HIG", [
        G("TU_HIG_foreign", "외세 영향", "Foreign Influence", "red",
          tip=("열린 항구마다 바깥의 입김이 쌓입니다. §Y60§!을 넘으면 존왕양이 봉기가 일어납니다.",
               "Outside influence that seeps in through every open port. Above §Y60§! the expel-the-foreigners uprising breaks out.")),
        G("TU_HIG_ports", "개항장", "Treaty Ports",
          tip=("바깥 배에 문을 연 항구입니다. 항구마다 매달 정치력 §G+0.5§!, 외세 영향 §R+2§!가 붙습니다.",
               "Harbours opened to foreign ships. Each gives §G+0.5§! political power and §R+2§! foreign influence per month.")),
        G("TU_HIG_shinobi", "닌자", "Shinobi", "green",
          tip=("막부가 부릴 수 있는 그림자들입니다. 작전 하나에 닌자 §Y2§!명이 듭니다.",
               "The shadows the Shogunate can call upon. Each operation takes §Y2§! shinobi.")),
    ]),
    ("IBE", [
        G("TU_IBE_threat", "바다의 위협", "Threat from the Sea", "red",
          tip=("심연에서 올라오는 것들의 기척입니다. 매달 오르며, 온전한 등대가 많을수록 덜 오릅니다. §Y70§! 이상이면 해안 마을이 침식됩니다.",
               "Signs of what rises from the deep. It grows every month, more slowly with each intact lighthouse. At §Y70§! or more, coastal towns are eroded.")),
        G("TU_IBE_cult", "심해교단 세력", "Deep Sea Cult", "teal",
          tip=("심해를 숭배하는 교단입니다. 매달 자라며, §Y20§!부터 바다의 위협을 더 올립니다. §Y40§!·§Y60§!·§Y80§!부터 포교, 등대 파괴, 봉기가 일어납니다. §Y40§!부터 안정도와 정치력도 깎입니다. 심판관의 나라 루트는 매달 세력을 깎습니다. 완전히 없앨 수 없습니다.",
               "The cult that worships the deep. It grows every month and adds to the sea threat from §Y20§!. Preaching, sabotage and uprisings start at §Y40§!, §Y60§! and §Y80§!. From §Y40§! it also drains stability and political power. The State of the Inquisitors wears it down every month. It can never be wiped out.")),
        G("TU_IBE_lighthouses", "해안의 등대", "Coastal Lighthouses", full=True,
          value=("불 밝힌 등대 [?TU_IBE_lighthouses|Y0]기 · §O꺼져 가는 등대 [?TU_IBE_lh_damaged|0]기§!",
                 "[?TU_IBE_lighthouses|Y0] lit · §O[?TU_IBE_lh_damaged|0] failing§!"),
          layers=[("orange", "TU_IBE_lh_damaged"), ("red", "TU_IBE_lh_severe")],
          tip=("다시 불을 밝힌 해안의 등대입니다. 온전한 등대 하나마다 바다의 위협이 덜 오릅니다.\\n칸 색: §Y금색§! 온전 · §O주황§! 손상 1단계 · §R빨강§! 손상 2단계. 손상된 등대는 위협을 막지 못합니다.",
               "Coastal lighthouses lit once more. Each intact one slows the rise of the threat from the sea.\\nCell colours: §Ygold§! intact, §Oorange§! damage stage 1, §Rred§! damage stage 2. Damaged lighthouses hold nothing back.")),
    ]),
    ("KAZ", [
        G("TU_KAZ_fame", "기사 명성", "Knightly Fame",
          tip=("경기장과 전장에서 얻은 카시미어 기사들의 이름값입니다.",
               "The renown Kazimierz's knights have earned in the arena and on the battlefield.")),
    ]),
    ("KJE", [
        G("TU_KJE_modern", "근대화", "Modernization",
          tip=("공장과 연구가 설산에 들어온 정도입니다. 근대화는 공장과 연구를, 전통은 신앙과 안정을 가져옵니다.",
               "How far factories and research have reached the snow mountains. Modernity brings industry and research; tradition brings faith and stability.")),
    ]),
    ("KZD", [
        G("TU_KZD_contracts", "맺은 용병 계약", "Active Mercenary Contracts", max=3,
          tip=("지금 맺고 있는 용병 계약입니다. 한 번에 §Y3§!건까지 맺을 수 있습니다.",
               "Mercenary contracts currently in force. Up to §Y3§! can run at once.")),
    ]),
    ("LAT", [
        G("TU_LAT_pilgrims", "순례자", "Pilgrims", "green",
          tip=("성도를 찾아온 순례자들입니다. 매달 늘어나고, 전쟁 중에는 줄어듭니다. 헌금·의용대·축제로 쓸 수 있습니다.",
               "Pilgrims who have come to the Holy City. They grow every month and dwindle in wartime. They can be spent on offerings, volunteers and festivals.")),
        G("TU_LAT_influence", "교황청 영향력", "Papal Influence", "blue",
          tip=("교황청의 목소리가 테라 곳곳에 닿는 정도입니다.",
               "How far the voice of the Papal See reaches across Terra.")),
    ]),
    ("LEI", [
        G("TU_LEI_resonance", "아츠 공명", "Arts Resonance", "green",
          tip=("연주회로 쌓아 올린 아츠의 울림입니다. 공명 §Y30§!으로 교향곡을 걸 수 있습니다.",
               "The resonance of Arts built up through concerts. §Y30§! resonance lets you stage a symphony.")),
        G("TU_LEI_electors", "여제 편 선제후", "Loyal Electors",
          tip=("여제를 지지하는 선제후입니다. §Y5§!명 이상이면 제국 칙령을 내릴 수 있습니다.",
               "Electors who stand with the Empresses. With §Y5§! or more, an Imperial Edict can be issued.")),
        G("TU_LEI_relics", "마왕의 유물", "Relics of the Demon King", "red",
          tip=("제국 곳곳에 흩어진 마왕 시대의 유물입니다.",
               "Relics of the Demon King's era scattered across the empire.")),
    ]),
    ("MIN", [
        G("TU_MIN_assembly", "민회 지지", "Assembly Support",
          tip=("민회가 정부를 믿고 따르는 정도입니다. 법안을 통과시킬 때 씁니다.",
               "How much the Assembly trusts the government. Spent to pass bills.")),
        G("TU_MIN_routes", "해상 교역로", "Sea Trade Routes", "green",
          tip=("다섯 도시를 바깥 세상과 잇는 바닷길입니다.",
               "Sea lanes linking the five cities to the wider world.")),
    ]),
    ("RHO", [
        G("TU_lmd", "보유 용문폐", "LMD on Hand", kind="number", value=("{v} LMD", "{v} LMD"),
          tip=("로도스 아일랜드의 운영 자금입니다. RIIC 업그레이드와 작전에 씁니다.",
               "Rhodes Island's operating funds, spent on RIIC upgrades and operations.")),
        G("TU_RHO_lmd_income", "월 수입", "Monthly Income", kind="number", value=("{v} LMD", "{v} LMD"),
          tip=("매달 들어오는 용문폐입니다. 무역소 레벨이 오르면 늘어납니다.",
               "LMD coming in every month. Rises with the Trading Post level.")),
        G("TU_RHO_riic_power", "RIIC 발전소", "RIIC Power Plant", "blue", max=3,
          tip=("최대 §Y3§!레벨입니다. 레벨마다 다른 시설의 레벨 상한이 1 오릅니다.",
               "Up to level §Y3§!. Each level raises the other facilities' level cap by 1.")),
        G("TU_RHO_riic_factory", "RIIC 제조소", "RIIC Factory", max=5, cap="TU_RHO_riic_cap",
          tip=("레벨마다 외부 무기 공장을 하나씩 더 얻습니다.",
               "Each level grants another offsite arms factory.")),
        G("TU_RHO_riic_trade", "RIIC 무역소", "RIIC Trading Post", max=5, cap="TU_RHO_riic_cap",
          tip=("레벨마다 외부 산업 단지를 하나씩 더 얻고, 월 용문폐 수입이 늘어납니다.",
               "Each level grants another offsite industrial complex and raises monthly LMD income.")),
        G("TU_RHO_riic_dorm", "RIIC 숙소", "RIIC Dormitory", "green", max=5, cap="TU_RHO_riic_cap",
          tip=("군 조직 회복과 사기를 높입니다.",
               "Improves army organisation recovery and morale.")),
        G("TU_RHO_riic_reception", "RIIC 응접실", "RIIC Reception Room", "green", max=5, cap="TU_RHO_riic_cap",
          tip=("정치력 획득을 높입니다. 라 레지스탕스가 있으면 정보망 획득도 오릅니다.",
               "Increases political power gain. With La Résistance, it also boosts intelligence network gain.")),
        G("TU_RHO_pmc_count", "PMC 계약", "PMC Contracts", kind="number",
          tip=("로도스 아일랜드가 맺고 있는 PMC 계약입니다.",
               "PMC contracts Rhodes Island currently holds.")),
    ]),
    ("RIM", [
        G("TU_RIM_infection", "광석병 감염률", "Oripathy Infection Rate", "red",
          tip=("광부와 주민 사이에 퍼진 광석병입니다. §Y60§!을 넘으면 파업과 집단 감염이 일어납니다.",
               "Oripathy spreading among miners and residents. Above §Y60§!, strikes and mass infections break out.")),
        G("TU_RIM_ore", "비축 원석", "Stockpiled Ore", "green",
          tip=("갱도에서 캐낸 원석입니다. 갱도마다 매달 §G+5§!씩 쌓입니다.",
               "Ore dug from the shafts. §G+5§! per shaft each month.")),
        G("TU_RIM_shafts", "원석 갱도", "Originium Shafts",
          tip=("운영 중인 원석 갱도입니다. 갱도마다 매달 광석 §G+5§!, 감염률 §R+1§!이 붙습니다.",
               "Operating Originium shafts. Each gives §G+5§! ore and §R+1§! infection per month.")),
        G("TU_RIM_settlements", "정착촌", "Settlements",
          tip=("황무지 위에 세운 정착촌입니다.",
               "Settlements raised on the wasteland.")),
    ]),
    ("SAM", [
        G("TU_SAM_grace", "숲의 은총", "Grace of the Forest", "green",
          tip=("숲이 사미에게 허락한 은총입니다. 정령 계약 하나마다 매달 §R-1§!씩 줄어듭니다. §Y20§! 아래로 떨어지면 숲이 분노합니다.",
               "The grace the forest grants the Sami. Each spirit pact costs §R-1§! per month. Below §Y20§!, the forest grows wrathful.")),
        G("TU_SAM_contact", "바깥과의 접촉", "Contact with the Outside",
          tip=("바깥 세상과 닿은 정도입니다.",
               "How far the Sami have come into contact with the outside world.")),
        G("TU_SAM_councils", "부족 회의", "Tribal Councils",
          tip=("열린 부족 회의입니다.",
               "Tribal councils that have been convened.")),
        G("TU_SAM_pacts", "정령 계약", "Spirit Pacts", "blue",
          tip=("맺은 정령 계약입니다. 동시에 §Y2§!개까지 맺을 수 있습니다.",
               "Spirit pacts in force. Up to §Y2§! at once.")),
    ]),
    ("SAR", [
        G("TU_SAR_gold", "황금", "Gold",
          tip=("대상단이 싣고 온 황금입니다. 대상단은 떠난 지 60일 뒤에 돌아옵니다.",
               "Gold brought home by the caravans, which return 60 days after setting out.")),
        G("TU_SAR_loyalty", "영주들의 충성", "Loyalty of the Lords", "blue",
          tip=("영주들이 파디샤를 섬기는 마음입니다. §Y30§! 아래로 떨어지면 반란이 일어날 수 있습니다.",
               "How faithfully the lords serve the Padishah. Below §Y30§!, rebellion may break out.")),
    ]),
    ("SIR", [
        G("TU_SIR_law", "법의 권위", "Authority of Law", "green",
          tip=("도시에 남아 있는 법의 무게입니다. 패밀리와 거래하면 약해지고, 단속하면 강해집니다.",
               "The weight the law still carries in the cities. Dealing with the Families weakens it; crackdowns strengthen it.")),
        G("TU_SIR_bellone", "벨로네 패밀리", "Bellone Family", "red",
          tip=("벨로네 패밀리의 영향력입니다. 매달 오르며, 거래하면 더 강해지고 단속하면 약해집니다.",
               "The Bellone Family's influence. It rises every month, grows with deals and shrinks with crackdowns.")),
        G("TU_SIR_gambino", "감비노 패밀리", "Gambino Family", "blue",
          tip=("감비노 패밀리의 영향력입니다. 매달 오르며, 거래하면 더 강해지고 단속하면 약해집니다.",
               "The Gambino Family's influence. It rises every month, grows with deals and shrinks with crackdowns.")),
        G("TU_SIR_saluzzo", "살루초 패밀리", "Saluzzo Family",
          tip=("살루초 패밀리의 영향력입니다. 매달 오르며, 거래하면 더 강해지고 단속하면 약해집니다.",
               "The Saluzzo Family's influence. It rises every month, grows with deals and shrinks with crackdowns.")),
    ]),
]

# 수치 -> 놓을 디시전 탭 (여러 탭이면 튜플). 탭은 항상 보이고, 안의 디시전은 content_lib 가 탭의 조건을 물려받아 중점으로 열린다
TABS = {
    "TU_BOL_control": "TU_BOL_war_category", "TU_BOL_weariness": "TU_BOL_war_category",
    "TU_BOL_victoria": "TU_BOL_patrons_category", "TU_BOL_columbia": "TU_BOL_patrons_category",
    "TU_COL_science": "TU_COL_rhine_category",
    "TU_HIG_foreign": "TU_HIG_ports_category", "TU_HIG_ports": "TU_HIG_ports_category",
    "TU_HIG_shinobi": "TU_HIG_shinobi_category",
    "TU_IBE_threat": "TU_IBE_coast_category", "TU_IBE_cult": "TU_IBE_coast_category", "TU_IBE_lighthouses": "TU_IBE_coast_category",
    "TU_KAZ_fame": "TU_KAZ_politics_category",
    "TU_KJE_modern": "TU_KJE_modern_category",
    "TU_KZD_contracts": "TU_KZD_mercenary_category",
    "TU_LAT_pilgrims": "TU_LAT_pilgrims_category", "TU_LAT_influence": "TU_LAT_covenant_category",
    "TU_LEI_resonance": "TU_LEI_arts_category", "TU_LEI_electors": "TU_LEI_electors_category",
    "TU_LEI_relics": "TU_LEI_relics_category",
    "TU_MIN_assembly": "TU_MIN_assembly_category", "TU_MIN_routes": "TU_MIN_sea_category",
    "TU_lmd": ("TU_RHO_riic_category", "TU_RHO_operations_category"), "TU_RHO_lmd_income": "TU_RHO_riic_category",
    "TU_RHO_riic_power": "TU_RHO_riic_category", "TU_RHO_riic_factory": "TU_RHO_riic_category",
    "TU_RHO_riic_trade": "TU_RHO_riic_category", "TU_RHO_riic_dorm": "TU_RHO_riic_category",
    "TU_RHO_riic_reception": "TU_RHO_riic_category", "TU_RHO_pmc_count": "TU_RHO_operations_category",
    "TU_RIM_infection": "TU_RIM_health_category", "TU_RIM_ore": "TU_RIM_mines_category",
    "TU_RIM_shafts": "TU_RIM_mines_category", "TU_RIM_settlements": "TU_RIM_settle_category",
    "TU_SAM_grace": "TU_SAM_spirits_category", "TU_SAM_pacts": "TU_SAM_spirits_category",
    "TU_SAM_contact": "TU_SAM_outside_category", "TU_SAM_councils": "TU_SAM_tribes_category",
    "TU_SAR_gold": "TU_SAR_caravans_category", "TU_SAR_loyalty": "TU_SAR_court_category",
    "TU_SIR_law": "TU_SIR_families_category", "TU_SIR_bellone": "TU_SIR_families_category",
    "TU_SIR_gambino": "TU_SIR_families_category", "TU_SIR_saluzzo": "TU_SIR_families_category",
}


def tabs_of(var):
    v = TABS[var]
    return (v,) if isinstance(v, str) else v


PANEL_TABS = sorted({c for v in TABS for c in tabs_of(v)})


def status_ui(category):
    return category.replace("_category", "_status_ui")
