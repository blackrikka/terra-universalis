#!/usr/bin/env python3
"""나라별 캐릭터 · 결말 지도자 · 국호 변경 데이터 (사양서 23). build_characters.py 와 merge_focus(focus_hooks) 가 쓴다.

캐릭터: (id 접미사, 한국어 이름, 영어 이름, 역할 목록, 초상화 GFX 또는 None)
  역할  ("L", 이념)                         국가 지도자 (중립 하위 이념: despotism oligarchism moderatism centrism,
                                            민주 liberalism, 파시즘 fascism_ideology)
        ("A", 슬롯, 특성)                   참모 (political_advisor / high_command / theorist)
        ("G", 공격, 방어, 계획, 보급)         군단장       ("M", …) 원수
start : 시작 때 영입할 캐릭터 (첫 번째가 지도자). 기존 대국은 지도자를 이미 영입하므로 참모·장군만.
hooks : {중점 id 접미사: [("leader", 캐릭터, 이념), ("name", 국호 키, 한국어, 영어, 한국어 형용, 영어 형용)]}
cast  : True 면 이 나라 캐릭터 파일 전체를 만든다 (build_countries 의 일반 지도자 대신). False 면 보강 파일만.
"""

GFX = "GFX_TU_portrait_%s"

COUNTRIES = {
    # ------------------------------------------------------------------ 카시미어
    "KAZ": dict(cast=True, chars=[
        ("chairman", "상업 연합회 의장", "Chairman of the Commercial Union", [("L", "liberalism")], None),
        ("mlynar", "믈리나르 니어", "Mlynar Nearl", [("L", "despotism"), ("G", 5, 4, 3, 3)], None),
        ("margaret", "마거릿 니어", "Margaret Nearl", [("L", "moderatism"), ("G", 4, 5, 3, 3)], None),
        ("blemishine", "마리아 니어", "Maria Nearl", [("A", "political_advisor", "tu_popular_knight")], None),
        ("zofia", "조피아", "Zofia", [("A", "high_command", "tu_chief_knight"), ("G", 4, 3, 3, 3)], None),
        ("fartooth", "파투스", "Fartooth", [("G", 4, 2, 3, 2)], None),
        ("ashlock", "애쉬록", "Ashlock", [("G", 3, 4, 2, 3)], None),
        ("union_broker", "연합회 재무 이사", "Union Finance Director", [("A", "political_advisor", "tu_union_financier")], None),
    ], start=["chairman", "blemishine", "union_broker", "zofia", "fartooth", "ashlock"], hooks={
        "shareholder_state": [("name", "UNION", "카시미어 상업 연합국", "Kazimierz Commercial Union", "카시미어의", "Kazimierzan")],
        "knight_kingdom": [("leader", "mlynar", "despotism"),
                           ("name", "KNIGHTS", "카시미어 기사왕국", "Knightly Kingdom of Kazimierz", "카시미어의", "Kazimierzan")],
        "knights_for_all": [("leader", "margaret", "moderatism"),
                            ("name", "FREE", "모두의 카시미어", "Kazimierz for All", "카시미어의", "Kazimierzan")],
    }),
    # ------------------------------------------------------------------ 컬럼비아
    "COL": dict(cast=True, chars=[
        ("president", "컬럼비아 대통령", "President of Columbia", [("L", "liberalism")], None),
        ("kristen", "크리스틴 라이트", "Kristen Wright", [("L", "oligarchism")], None),
        ("frontier_rep", "개척자 연합 대표", "Frontier Union Representative", [("L", "moderatism")], None),
        ("silence", "사일런스", "Silence", [("A", "political_advisor", "tu_arts_scholar")], None),
        ("muelsyse", "뮤엘시스", "Muelsyse", [("A", "theorist", "tu_theorist_arts")], None),
        ("saria", "사리아", "Saria", [("A", "high_command", "tu_chief_defender"), ("M", 4, 6, 4, 4)], None),
        ("sheriff", "개척지 보안관", "Frontier Sheriff", [("G", 4, 3, 3, 3)], None),
        ("guard_general", "연방 경비대장", "Federal Guard General", [("G", 3, 4, 4, 3)], None),
    ], start=["president", "silence", "muelsyse", "saria", "sheriff", "guard_general"], hooks={
        "corporate_republic": [("leader", "kristen", "oligarchism"),
                               ("name", "CORP", "컬럼비아 기업 공화국", "Corporate Republic of Columbia", "컬럼비아의", "Columbian")],
        "frontier_federation": [("leader", "frontier_rep", "moderatism"),
                                ("name", "FRONTIER", "컬럼비아 개척자 연방", "Frontier Federation of Columbia", "컬럼비아의", "Columbian")],
        "republic_guard": [("name", "FED", "컬럼비아 연방 공화국", "Federal Republic of Columbia", "컬럼비아의", "Columbian")],
    }),
    # ------------------------------------------------------------------ 라테라노
    "LAT": dict(cast=True, chars=[
        ("pope", "교황", "The Pope", [("L", "despotism")], None),
        ("notary", "공증청장", "Chief Notary", [("L", "centrism")], None),
        ("federico", "페데리코", "Federico", [("A", "political_advisor", "tu_inquisitor")], None),
        ("mostima", "모스티마", "Mostima", [("A", "political_advisor", "tu_diplomat")], None),
        ("exusiai", "엑시아", "Exusiai", [("G", 5, 2, 3, 3)], None),
        ("fiammetta", "피아메타", "Fiammetta", [("A", "high_command", "tu_chief_knight"), ("G", 5, 3, 3, 2)], None),
        ("lemuen", "레미엔", "Lemuen", [("G", 4, 3, 4, 3)], None),
    ], start=["pope", "federico", "mostima", "exusiai", "fiammetta", "lemuen"], hooks={
        "papal_theocracy": [("name", "PAPAL", "라테라노 교황국", "Papal State of Laterano", "라테라노의", "Lateran")],
        "notarial_republic": [("leader", "notary", "centrism"),
                              ("name", "NOTARIAL", "라테라노 공증인 공화국", "Notarial Republic of Laterano", "라테라노의", "Lateran")],
        "open_city": [("name", "OPEN", "열린 성도 라테라노", "Open Holy City of Laterano", "라테라노의", "Lateran")],
    }),
    # ------------------------------------------------------------------ 라이타니엔
    "LEI": dict(cast=True, chars=[
        ("empresses", "쌍둥이 여제", "The Twin Empresses", [("L", "despotism")], None),
        ("elector", "선제후 회의 의장", "Speaker of the Electors", [("L", "oligarchism")], None),
        ("witch_king", "마왕", "The Witch King", [("L", "despotism")], None),
        ("ebenholz", "에벤홀츠", "Ebenholz", [("A", "political_advisor", "tu_arts_scholar")], None),
        ("conductor", "궁정 악장", "Court Kapellmeister", [("A", "theorist", "tu_theorist_arts")], None),
        ("viviana", "비비아나", "Viviana", [("A", "high_command", "tu_chief_knight"), ("G", 4, 3, 3, 3)], None),
        ("arts_general", "아츠 근위대장", "Arts Guard Commander", [("G", 3, 4, 4, 3)], None),
    ], start=["empresses", "ebenholz", "conductor", "viviana", "arts_general"], hooks={
        "twin_empresses": [("name", "EMPIRE", "라이타니엔 쌍둥이 제국", "Twin Empire of Leithanien", "라이타니엔의", "Leithanian")],
        "electoral_federation": [("leader", "elector", "oligarchism"),
                                 ("name", "ELECTORAL", "라이타니엔 선제후 연방", "Electoral Federation of Leithanien", "라이타니엔의", "Leithanian")],
        "witch_king_return": [("leader", "witch_king", "despotism"),
                              ("name", "WITCH", "마왕의 라이타니엔", "Leithanien of the Witch King", "라이타니엔의", "Leithanian")],
    }),
    # ------------------------------------------------------------------ 이베리아
    "IBE": dict(cast=True, chars=[
        ("grand_inquisitor", "대심판관", "Grand Inquisitor", [("L", "fascism_ideology")], None),
        ("king", "이베리아 국왕", "King of Iberia", [("L", "despotism")], None),
        ("irene", "아이린", "Irene", [("L", "moderatism"), ("A", "political_advisor", "tu_inquisitor")], None),
        ("ulpianus", "울피아누스", "Ulpianus", [("L", "despotism"), ("A", "high_command", "tu_chief_defender"), ("G", 5, 5, 3, 2)], None),
        ("skadi", "스카디", "Skadi", [("L", "despotism"), ("G", 6, 3, 2, 2)], None),
        ("specter", "스펙터", "Specter", [("L", "despotism"), ("G", 5, 3, 2, 2)], None),
        ("gladiia", "글래디아", "Gladiia", [("L", "despotism"), ("A", "theorist", "tu_theorist_tactics"), ("G", 4, 4, 4, 3)], None),
        ("ishar_mla", "이샤믈라", "Ishar-mla", [("L", "despotism")], None),     # 숨은 루트 (이벤트 tu_ibe_ev.41)
    ], start=["grand_inquisitor", "irene", "ulpianus", "skadi", "specter", "gladiia"], hooks={
        "inquisitor_state": [("name", "INQUISITION", "이베리아 심판국", "Inquisitorial State of Iberia", "이베리아의", "Iberian")],
        "crown_restored": [("leader", "king", "despotism"),
                           ("name", "KINGDOM", "이베리아 왕국", "Kingdom of Iberia", "이베리아의", "Iberian")],
        "sea_reconciliation": [("leader", "irene", "moderatism"),
                               ("name", "NEW", "새 이베리아", "New Iberia", "이베리아의", "Iberian")],
        # hunter_skadi: 지도자는 중점이 아니라 이벤트 tu_ibe_ev.42 가 고른다 (사양서 38)
        "ishar_finale": [("name", "DEEP", "심해", "The Deep", "심해의", "Deep")],
    }),
    # ------------------------------------------------------------------ 사르곤
    "SAR": dict(cast=True, chars=[
        ("padishah", "파디샤", "The Padishah", [("L", "despotism")], None),
        ("lords", "영주 회의 의장", "Speaker of the Lords", [("L", "oligarchism")], None),
        ("guildmaster", "황금 상인 조합장", "Master of the Golden Guild", [("L", "oligarchism")], None),
        ("beeswax", "비즈왁스", "Beeswax", [("A", "political_advisor", "tu_arts_scholar")], None),
        ("vizier", "궁정 대신", "Grand Vizier", [("A", "political_advisor", "tu_union_financier")], None),
        ("carnelian", "카넬리안", "Carnelian", [("A", "high_command", "tu_chief_logistics"), ("M", 5, 4, 4, 4)], None),
        ("ifrit", "이프리트", "Ifrit", [("G", 6, 1, 2, 2)], None),
        ("desert_rider", "사막 기병대장", "Desert Rider Captain", [("G", 4, 3, 3, 4)], None),
    ], start=["padishah", "beeswax", "vizier", "carnelian", "ifrit", "desert_rider"], hooks={
        "padishah_empire": [("name", "EMPIRE", "사르곤 제국", "Sargon Empire", "사르곤의", "Sargonian")],
        "lords_confederation": [("leader", "lords", "oligarchism"),
                                ("name", "LORDS", "사르곤 영주 연합", "Sargon Lords' Confederation", "사르곤의", "Sargonian")],
        "golden_council": [("leader", "guildmaster", "oligarchism"),
                           ("name", "GOLDEN", "사르곤 황금 상인국", "Golden Merchant State of Sargon", "사르곤의", "Sargonian")],
    }),
    # ------------------------------------------------------------------ 시라쿠사
    "SIR": dict(cast=True, chars=[
        ("elder_don", "원로 대부", "The Elder Don", [("L", "oligarchism")], None),
        ("family_head", "패밀리 평의회", "The Family Council", [("L", "oligarchism")], None),
        ("penance", "라비니아", "Lavinia", [("L", "moderatism"), ("A", "political_advisor", "tu_inquisitor")], None),
        ("wolf_heir", "늑대 군주", "The Wolf Lord", [("L", "despotism")], None),
        ("texas", "텍사스", "Texas", [("A", "high_command", "tu_chief_logistics"), ("G", 4, 3, 3, 4)], None),
        ("lappland", "라플란드", "Lappland", [("G", 6, 2, 2, 2)], None),
        ("consigliere", "패밀리 고문", "Family Consigliere", [("A", "political_advisor", "tu_spymaster")], None),
        ("valencina", "발렌치나", "Valencina", [("G", 6, 3, 3, 4)], None),     # 이스터에그 (sir.py tu_sir_ev.37)
    ], start=["elder_don", "penance", "consigliere", "texas", "lappland"], hooks={
        "family_council": [("leader", "family_head", "oligarchism"),
                           ("name", "FAMILIES", "시라쿠사 패밀리 연합", "Siracusan Family Union", "시라쿠사의", "Siracusan")],
        "rule_of_law": [("leader", "penance", "moderatism"),
                        ("name", "LAW", "법의 시라쿠사", "Siracusa of Law", "시라쿠사의", "Siracusan")],
        "wolf_lord": [("leader", "wolf_heir", "despotism"),
                      ("name", "WOLF", "늑대 군주의 시라쿠사", "Siracusa of the Wolf Lord", "시라쿠사의", "Siracusan")],
    }),
    # ------------------------------------------------------------------ 쉐라그
    "KJE": dict(cast=True, chars=[
        ("elders", "장로 회의", "Council of Elders", [("L", "oligarchism")], None),
        ("silverash", "실버애쉬", "SilverAsh", [("L", "centrism"), ("A", "political_advisor", "tu_union_financier")], None),
        ("pramanix", "프라마닉스", "Pramanix", [("L", "despotism")], None),
        ("houses", "세 가문 평의회", "Council of the Three Houses", [("L", "oligarchism")], None),
        ("cliffheart", "클리프하트", "Cliffheart", [("G", 4, 3, 3, 3)], None),
        ("courier", "쿠리어", "Courier", [("A", "high_command", "tu_chief_logistics"), ("G", 3, 4, 3, 4)], None),
    ], start=["elders", "silverash", "cliffheart", "courier"], hooks={
        "modern_kjerag": [("leader", "silverash", "centrism"),
                          ("name", "MODERN", "근대 쉐라그", "Modern Kjerag", "쉐라그의", "Kjeragandr")],
        "saintess_theocracy": [("leader", "pramanix", "despotism"),
                               ("name", "SAINTESS", "쉐라그 성녀국", "Saintess State of Kjerag", "쉐라그의", "Kjeragandr")],
        "houses_united": [("leader", "houses", "oligarchism"),
                          ("name", "HOUSES", "쉐라그 삼가 연합", "Union of the Three Houses", "쉐라그의", "Kjeragandr")],
    }),
    # ------------------------------------------------------------------ 극동
    "HIG": dict(cast=True, chars=[
        ("regent", "조정 섭정", "Court Regent", [("L", "oligarchism")], None),
        ("shogun", "쇼군", "The Shogun", [("L", "despotism")], None),
        ("premier", "개국파 수상", "Reformist Premier", [("L", "centrism")], None),
        ("emperor", "천황", "The Emperor", [("L", "despotism")], None),
        ("saga", "사가", "Saga", [("A", "political_advisor", "tu_diplomat")], None),
        ("akafuyu", "아카후유", "Akafuyu", [("A", "high_command", "tu_chief_knight"), ("G", 5, 3, 2, 3)], None),
        ("shinobi_master", "닌자 두령", "Shinobi Master", [("A", "political_advisor", "tu_spymaster")], None),
        ("samurai_general", "무사 대장", "Samurai General", [("G", 4, 4, 3, 3)], None),
    ], start=["regent", "saga", "shinobi_master", "akafuyu", "samurai_general"], hooks={
        "shogunate": [("leader", "shogun", "despotism"), ("name", "SHOGUNATE", "극동 막부", "Far East Shogunate", "극동의", "Far Eastern")],
        "open_far_east": [("leader", "premier", "centrism"), ("name", "OPEN", "개국 극동", "Open Far East", "극동의", "Far Eastern")],
        "imperial_restoration": [("leader", "emperor", "despotism"),
                                 ("name", "EMPIRE", "극동 제국", "Far Eastern Empire", "극동의", "Far Eastern")],
    }),
    # ------------------------------------------------------------------ 미노스
    "MIN": dict(cast=True, chars=[
        ("archon", "민회 집정관", "Archon of the Assembly", [("L", "conservatism")], None),
        ("elder", "원로 회의장", "Head of the Elders", [("L", "oligarchism")], None),
        ("strategos", "해상 집정관", "Thalassocrat", [("L", "despotism")], None),
        ("philosopher", "아카데미아 학두", "Scholarch of the Academy", [("A", "theorist", "tu_theorist_tactics")], None),
        ("oracle", "신탁 사제", "Oracle Priestess", [("A", "political_advisor", "tu_diplomat")], None),
        ("hoplite_general", "중장 보병 대장", "Hoplite General", [("A", "high_command", "tu_chief_defender"), ("G", 3, 5, 3, 3)], None),
        ("trade_captain", "상단 호위대장", "Caravan Guard Captain", [("G", 4, 3, 3, 4)], None),
    ], start=["archon", "philosopher", "oracle", "hoplite_general", "trade_captain"], hooks={
        "democratic_polis": [("name", "POLIS", "미노스 민주 연맹", "Democratic League of Minos", "미노스의", "Minoan")],
        "rule_of_elders": [("leader", "elder", "oligarchism"), ("name", "ELDERS", "미노스 원로국", "Minos of the Elders", "미노스의", "Minoan")],
        "thalassocracy": [("leader", "strategos", "despotism"),
                          ("name", "EMPIRE", "미노스 패권 제국", "Minoan Hegemony", "미노스의", "Minoan")],
    }),
    # ------------------------------------------------------------------ 림 빌리튼
    "RIM": dict(cast=True, chars=[
        ("governor", "광산 총독", "Mining Governor", [("L", "oligarchism")], None),
        ("ceo", "회사 이사장", "Company Chairman", [("L", "oligarchism")], None),
        ("union_leader", "광부 노조 위원장", "Miners' Union Leader", [("L", "marxism")], None),
        ("haven_rep", "안식처 대표", "Haven Representative", [("L", "moderatism")], None),
        ("mine_engineer", "수석 갱도 기사", "Chief Mine Engineer", [("A", "political_advisor", "tu_originium_magnate")], None),
        ("physician", "광석병 전문의", "Oripathy Physician", [("A", "political_advisor", "tu_oripathy_physician")], None),
        ("security_chief", "회사 경비대장", "Company Security Chief", [("A", "high_command", "tu_chief_defender"), ("G", 3, 4, 3, 3)], None),
        ("foreman_general", "광부 의용대장", "Miners' Militia Captain", [("G", 4, 3, 2, 3)], None),
    ], start=["governor", "mine_engineer", "physician", "security_chief", "foreman_general"], hooks={
        "corporate_rule": [("leader", "ceo", "oligarchism"),
                           ("name", "COMPANY", "림 빌리튼 회사국", "Rim Billiton Company State", "림 빌리튼의", "Rim Billiton")],
        "workers_rule": [("leader", "union_leader", "marxism"),
                         ("name", "WORKERS", "림 빌리튼 노동자 자치령", "Rim Billiton Workers' Commune", "림 빌리튼의", "Rim Billiton")],
        "infected_haven": [("leader", "haven_rep", "moderatism"),
                           ("name", "HAVEN", "감염자의 안식처", "Haven of the Infected", "안식처의", "Haven")],
    }),
    # ------------------------------------------------------------------ 사미
    "SAM": dict(cast=True, chars=[
        ("elder", "숲의 원로", "Elder of the Forest", [("L", "despotism")], None),
        ("shaman", "숲의 무녀", "Priestess of the Forest", [("L", "despotism"), ("A", "theorist", "tu_theorist_arts")], None),
        ("chieftain", "부족 연방 의장", "Chief of the Tribal Federation", [("L", "oligarchism")], None),
        ("envoy", "외교 대표", "Envoy to the World", [("L", "centrism"), ("A", "political_advisor", "tu_diplomat")], None),
        ("hunter", "사냥꾼 대장", "Hunt Master", [("A", "high_command", "tu_chief_logistics"), ("G", 4, 3, 3, 4)], None),
        ("witch", "얼음 마녀", "Ice Witch", [("G", 5, 3, 3, 2)], None),
    ], start=["elder", "shaman", "envoy", "hunter", "witch"], hooks={
        "forest_theocracy": [("leader", "shaman", "despotism"),
                             ("name", "FOREST", "숲의 신정 사미", "Forest Theocracy of Sami", "사미의", "Sami")],
        "tribal_federation": [("leader", "chieftain", "oligarchism"),
                              ("name", "FEDERATION", "사미 부족 연방", "Sami Tribal Federation", "사미의", "Sami")],
        "open_sami": [("leader", "envoy", "centrism"), ("name", "OPEN", "열린 사미", "Open Sami", "사미의", "Sami")],
    }),
    # ------------------------------------------------------------------ 볼리바르
    "BOL": dict(cast=True, chars=[
        ("provisional", "임시 대통령", "Provisional President", [("L", "liberalism")], None),
        ("president", "볼리바르 대통령", "President of Bolivar", [("L", "liberalism")], None),
        ("col_governor", "컬럼비아 총독", "Columbian Governor", [("L", "oligarchism")], None),
        ("vic_governor", "빅토리아 총독", "Victorian Governor", [("L", "despotism")], None),
        ("rebel_chief", "반군 사령관", "Rebel Commander", [("G", 4, 3, 2, 3)], None),
        ("army_chief", "정부군 참모총장", "Chief of the Government Army", [("A", "high_command", "tu_chief_defender"), ("G", 3, 4, 3, 3)], None),
        ("coffee_baron", "커피 농장주", "Coffee Baron", [("A", "political_advisor", "tu_union_financier")], None),
    ], start=["provisional", "coffee_baron", "army_chief", "rebel_chief"], hooks={
        "bolivar_republic": [("leader", "president", "liberalism"),
                             ("name", "REPUBLIC", "볼리바르 공화국", "Republic of Bolivar", "볼리바르의", "Bolivarian")],
        "columbian_protectorate": [("leader", "col_governor", "oligarchism"),
                                   ("name", "COLPROT", "컬럼비아 보호령 볼리바르", "Columbian Protectorate of Bolivar", "볼리바르의", "Bolivarian")],
        "victorian_protectorate": [("leader", "vic_governor", "despotism"),
                                   ("name", "VICPROT", "빅토리아 보호령 볼리바르", "Victorian Protectorate of Bolivar", "볼리바르의", "Bolivarian")],
    }),
    # ------------------------------------------------------------------ 기존 대국 보강 (지도자는 이미 있음)
    "KZD": dict(cast=False, chars=[
        ("commission", "카즈델 군사위원회", "Kazdel Military Commission", [("L", "fascism_ideology")], None),
        ("six_kings_lead", "육왕 평의회", "Council of the Six Kings", [("L", "oligarchism")], None),
        ("w_leader", "W", "W", [("L", "despotism")], GFX % "w"),
        ("logos", "로고스", "Logos", [("A", "political_advisor", "tu_arts_scholar")], None),
        ("hedley", "헤들리", "Hedley", [("A", "high_command", "tu_mercenary_broker")], None),
        ("mudrock", "머드락", "Mudrock", [("G", 4, 5, 3, 3)], None),
        ("broker", "용병 중개인", "Mercenary Broker", [("A", "political_advisor", "tu_mercenary_broker")], None),
    ], start=["commission", "logos", "broker", "hedley", "mudrock"], hooks={
        "theresis_throne": [("leader_existing", "TU_KZD_theresis", "fascism_ideology")],
        "empire_finale": [("name", "EMPIRE", "카즈델 제국", "Kazdel Empire", "카즈델의", "Kazdelian")],
        "new_empire": [("name", "NEWEMPIRE", "신 카즈델", "New Kazdel", "카즈델의", "Kazdelian")],
        "sixfold_throne": [("leader", "six_kings_lead", "oligarchism"),
                           ("name", "SIX", "육왕의 카즈델", "Kazdel of the Six Kings", "카즈델의", "Kazdelian")],
        "merc_kingdom": [("leader", "w_leader", "despotism"),
                         ("name", "MERC", "카즈델 용병 왕국", "Mercenary Kingdom of Kazdel", "카즈델의", "Kazdelian")],
    }),
    "URS": dict(cast=False, chars=[
        ("junta", "군정 평의회", "Military Junta", [("L", "fascism_ideology")], None),
        ("regent", "섭정 귀족", "Noble Regent", [("L", "oligarchism")], None),
        ("democrat", "민주당 대표", "Democratic Party Leader", [("L", "liberalism")], None),
        ("chancellor", "제국 재상", "Imperial Chancellor", [("A", "political_advisor", "tu_union_financier")], None),
        ("okhrana", "비밀경찰 국장", "Head of the Secret Police", [("A", "political_advisor", "tu_spymaster")], None),
        ("chief_of_staff", "총참모장", "Chief of the General Staff", [("A", "high_command", "tu_chief_defender")], None),
    ], start=["chancellor", "okhrana", "chief_of_staff"], hooks={
        "iron_regime": [("leader", "junta", "fascism_ideology"), ("name", "JUNTA", "우르수스 군정", "Ursus Military State", "우르수스의", "Ursine")],
        "noble_regency": [("leader", "regent", "oligarchism"), ("name", "REGENCY", "우르수스 섭정국", "Ursus Regency", "우르수스의", "Ursine")],
        "reform_democratic_party": [("leader", "democrat", "liberalism"),
                                    ("name", "REPUBLIC", "우르수스 공화국", "Ursine Republic", "우르수스의", "Ursine")],
    }),
    "VIC": dict(cast=False, chars=[
        ("chancellor", "재무 대신", "Chancellor of the Exchequer", [("A", "political_advisor", "tu_union_financier")], None),
        ("spymaster", "왕실 정보국장", "Royal Spymaster", [("A", "political_advisor", "tu_spymaster")], None),
        ("field_marshal", "원정군 원수", "Field Marshal of the Expedition", [("A", "high_command", "tu_chief_drill"), ("M", 4, 4, 5, 4)], None),
    ], start=["chancellor", "spymaster", "field_marshal"], hooks={}),
    "LGM": dict(cast=False, chars=[
        ("ch_en_aide", "근위국 부국장", "Deputy of the Guard Department", [("G", 3, 4, 4, 3)], None),
    ], start=["ch_en_aide"], hooks={
        "free_city_declaration": [("name", "FREE", "자유 도시 용문", "Free City of Lungmen", "용문의", "Lungmen")],
    }),
    "RHO": dict(cast=False, chars=[
        ("ace", "엘리트 오퍼레이터 대장", "Elite Operator Captain", [("G", 5, 4, 4, 3)], None),
        ("closure", "클로저", "Closure", [("A", "political_advisor", "tu_originium_magnate")], None),
    ], start=["ace", "closure"], hooks={
        "ark_mission": [("name", "ARK", "테라의 방주", "Ark of Terra", "방주의", "Ark")],
    }),
    "REU": dict(cast=False, chars=[
        ("crownslayer", "크라운슬레이어", "Crownslayer", [("G", 5, 2, 3, 3)], None),
        ("mephisto", "메피스토", "Mephisto", [("A", "political_advisor", "tu_oripathy_physician")], None),
    ], start=["crownslayer", "mephisto"], hooks={}),
}

# 코스메틱 태그 나라 색 (common/countries/cosmetic.txt): 국호 키 -> (지도 색 RGB, UI 색 RGB)
COSMETIC_COLORS = {
    "TU_IBE_DEEP": ((14, 22, 58), (40, 60, 120)),
}

# 테라 참모 특성 (common/country_leader/tu_advisor_traits.txt)
TRAITS = {
    "tu_union_financier": ("재정가", "Financier", 10, {"political_power_factor": 0.10, "consumer_goods_factor": -0.02}),
    "tu_arts_scholar": ("아츠 학자", "Arts Scholar", 2, {"research_speed_factor": 0.05}),
    "tu_originium_magnate": ("원석 사업가", "Originium Magnate", 10, {"production_speed_industrial_complex_factor": 0.10,
                                                                   "production_speed_arms_factory_factor": 0.10}),
    "tu_spymaster": ("첩보 수장", "Spymaster", 13, {"stability_factor": 0.05, "political_power_factor": 0.05}),
    "tu_oripathy_physician": ("광석병 전문의", "Oripathy Physician", 4, {"stability_factor": 0.05, "monthly_population": 0.10}),
    "tu_diplomat": ("외교관", "Diplomat", 3, {"political_power_factor": 0.10, "stability_factor": 0.03}),
    "tu_mercenary_broker": ("용병 중개인", "Mercenary Broker", 7, {"conscription_factor": 0.05, "experience_gain_army": 0.05}),
    "tu_inquisitor": ("심판관", "Inquisitor", 13, {"stability_factor": 0.07, "war_support_factor": 0.05}),
    "tu_popular_knight": ("민중의 기사", "Knight of the People", 3, {"stability_factor": 0.05, "war_support_factor": 0.05}),
    "tu_chief_knight": ("기사단장", "Knight Commander", 7, {"army_attack_factor": 0.08, "experience_gain_army": 0.05}),
    "tu_chief_defender": ("수호대장", "Warden", 7, {"army_defence_factor": 0.08, "experience_gain_army": 0.05}),
    "tu_chief_logistics": ("병참의 달인", "Master of Logistics", 7, {"supply_consumption_factor": -0.08, "experience_gain_army": 0.05}),
    "tu_chief_drill": ("훈련 교관", "Drill Master", 7, {"training_time_army_factor": -0.10, "experience_gain_army": 0.05}),
    "tu_theorist_tactics": ("전술 이론가", "Tactics Theorist", 2, {"experience_gain_army": 0.15}),
    "tu_theorist_arts": ("아츠 전술가", "Arts Tactician", 2, {"research_speed_factor": 0.03, "experience_gain_army": 0.10}),
}

# ------------------------------------------------------------------ 숨은 루트 (사양서 30, tools/focusgen/hidden_routes.py)
COUNTRIES["URS"]["chars"].append(("kashchey", "코셰이", "Kashchey", [("L", "despotism")], None))
COUNTRIES["KZD"]["chars"].append(("babel_assembly", "바벨 평의회", "Council of Babel", [("L", "oligarchism")], None))
COUNTRIES["SAM"]["chars"].append(("forest_will", "숲의 의지", "Will of the Forest", [("L", "despotism")], None))
_HIDDEN = {
    "URS": {"serpent_finale": [("name", "SERPENT", "검은 뱀의 제국", "Empire of the Black Serpent", "우르수스의", "Ursine")]},
    "REU": {"patriot_finale": [("name", "PATRIOT", "감염자 공화국", "Republic of the Infected", "감염자의", "Infected")]},
    "KZD": {"babel_finale": [("name", "BABEL", "새 바벨", "New Babel", "바벨의", "Babel"),
                             ("me", ["theresis_throne", "sixfold_throne", "merc_kingdom"])]},
    "SAM": {"forest_finale": [("name", "LIVING", "살아 있는 숲", "The Living Forest", "숲의", "Forest"),
                              ("me", ["forest_theocracy", "tribal_federation", "open_sami"])]},
    "COL": {"rhine_finale": [("name", "RHINE", "라인 공화국", "The Rhine Republic", "라인의", "Rhine"),
                             ("me", ["republic_guard", "corporate_republic", "frontier_federation"])]},
    "KJE": {"frozen_finale": [("name", "FROZEN", "얼어붙은 왕국", "The Frozen Kingdom", "얼어붙은", "Frozen"),
                              ("me", ["modern_kjerag", "saintess_theocracy", "houses_united"])]},
    "LGM": {"guard_finale": [("name", "GUARD", "용문 근위국", "Lungmen Guard State", "용문의", "Lungmen")]},
    "YAN": {"sui_dream_finale": [("name", "SUI", "세", "Sui", "세의", "Sui")]},
}
for _t, _h in _HIDDEN.items():
    COUNTRIES.setdefault(_t, dict(cast=False, chars=[], start=[], hooks={}))["hooks"].update(_h)
COSMETIC_COLORS.update({
    "TU_URS_SERPENT": ((38, 12, 16), (110, 40, 50)),
    "TU_REU_PATRIOT": ((150, 40, 40), (190, 80, 80)),
    "TU_KZD_BABEL": ((214, 200, 160), (214, 200, 160)),
    "TU_SAM_LIVING": ((18, 72, 34), (60, 130, 80)),
    "TU_COL_RHINE": ((40, 170, 170), (80, 200, 200)),
    "TU_KJE_FROZEN": ((205, 228, 245), (205, 228, 245)),
    "TU_LGM_GUARD": ((40, 70, 130), (80, 110, 170)),
    "TU_YAN_SUI": ((140, 20, 30), (190, 60, 60)),
})

# 손으로 만든 캐릭터 파일의 지도자 이념 덮어쓰기 (사양서 42: 나라마다 시작 이념이 다르다). build_characters 가 적용한다.
LEADER_IDEOLOGY = {
    "TU_URS_emperor": "fascism_ideology",       # 우르수스 제국 (파시즘)
    "TU_VIC_dukes_council": "conservatism",      # 빅토리아 대공 의회 (민주)
    "TU_REU_talulah": "marxism",                 # 리유니온 (공산)
    "TU_KZD_theresis": "fascism_ideology",       # 테레시스 (카즈델 파시즘)
    "TU_REU_patriot_leader": "marxism",
}
