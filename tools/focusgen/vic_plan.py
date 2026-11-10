# 빅토리아 정리 계획 (사양서 79)
# MERGE: 없앨 중점 -> 합쳐 남기는 중점 (효과를 합침, 자식은 남기는 쪽으로)
MERGE = {
 # 대공
 "duk_free_labour":"duk_tenancy", "duk_guild_break":"duk_guild_pact", "duk_banking_house":"duk_treasury_loans",
 "ducal_arsenal_alt":"ducal_arsenal",
 # 아슬란
 "glasgow_volunteers_alt":"glasgow_volunteers", "asl_docks_industry_alt":"asl_docks_industry", "asl_customs":"asl_smuggling",
 # 드라코
 "drc_tara_truce":"drc_tara_crackdown", "drc_flame_academies_alt":"drc_flame_academies", "drc_flame_bastion":"drc_flame_drill",
 "drc_ash_laborers_alt":"drc_ash_laborers", "drc_hostage_law":"drc_loyal_dublinn", "drc_war_fund_alt":"drc_war_fund",
 # 의회
 "par_union_law":"par_guild_charter", "par_tech_schools":"par_public_schools", "par_steel_rail_alt":"par_steel_rail",
 "par_free_elections_alt":"par_free_elections", "par_veterans_bill_alt":"par_veterans_bill", "par_civil_rights_alt":"par_civil_rights",
 # 경제
 "eco_airship_fleet_alt":"eco_airship_fleet", "kzd_mercenaries_alt":"kzd_mercenaries",
}
# DELETE: 없앤다 (자식은 부모에게)
DELETE = [
 "status_quo",
 # 대공
 "duk_council_law","duk_council_law_alt","duk_private_guard","duk_rail_concession","duk_rail_concession_alt","duk_war_cabinet","duk_war_cabinet_alt",
 "duk_fortified_estates_alt",
 # 아슬란
 "asl_glasgow_pilgrimage","asl_glasgow_pilgrimage_alt","asl_city_watch","asl_city_watch_alt","asl_street_law","asl_gang_courts",
 "asl_loyal_regiment","asl_loyal_regiment_alt",
 # 드라코
 "drc_sky_flames","drc_sky_flames_alt","drc_martial_courts","drc_martial_courts_alt","drc_veteran_cadre","drc_veteran_cadre_alt",
 "drc_secret_radio","drc_secret_radio_alt",
 # 의회
 "par_pamphlets","par_pamphlets_alt","par_monarch_pension","par_monarch_pension_alt","par_colonial_office","par_colonial_office_alt",
 "par_police_reform","par_police_reform_alt",
 # 경제
 "eco_arms_contracts","eco_urban_housing","eco_grand_bridge","eco_workers_guild","eco_steam_cavalry","eco_vanguard",
 "eco_harbour_grid","eco_fighter_tactics","eco_anti_air_belt",
]
