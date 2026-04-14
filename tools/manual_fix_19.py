import json
from pathlib import Path

base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
sid_path = base / "vertex_batch/merged/sid_to_vi.json"
sid_to_vi = json.loads(sid_path.read_text(encoding="utf-8"))

updates = {
    "s028363": "Nhấn {Key:Key_NorAttack} liên tục, {Key:Key_Roll}→{Key:Key_NorAttack}, hoặc {Key:Key_Jump}→{Key:Key_NorAttack} để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_CresecentAura_2_LV1}.<br/><br/>  Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 2]",
    "s031447": "Nhấn {Key:Key_NorAttack} liên tục, {Key:Key_Roll}→{Key:Key_NorAttack}, hoặc {Key:Key_Jump}→{Key:Key_NorAttack} để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_CresecentAura_1_LV1}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 2]",
    "s036281": "Các đòn tấn công cường hóa Lôi có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_LightningBreath_LV1#Orbs of Lightning} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpLightning#Lightning}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element} Lv. 1 trở lên]",
    "s039876": "Nhấn {Key:Key_NorAttack} liên tục, {Key:Key_Roll}→{Key:Key_NorAttack}, hoặc {Key:Key_Jump}→{Key:Key_NorAttack} để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_SwordAura_LV1}.<br/><br/>  Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 2]",
    "s042861": "Các đòn tấn công cường hóa Phong có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_Karanda#Pillar of Wind} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpWind#Wind}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element}: Lv. 1 trở lên]",
    "s046109": "Các đòn tấn công cường hóa Băng có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_FrostBreath_LV1#Frost Hail} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpIce#Frost}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element}: Lv. 1 trở lên]",
    "s046549": "Các đòn tấn công cường hóa Hỏa có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_Bastier#Flames of Judgment} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpFire#Flame}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element}: Lv. 1 trở lên]",
    "s050951": "Nhấn {Key:Key_Guard} ngay trước khi bị đánh trúng để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_TarandusWarrior_WarHammer}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 1]",
    "s058918": "Nhấn {Key:Key_NorAttack} liên tục, {Key:Key_Roll}→{Key:Key_NorAttack}, hoặc {Key:Key_Jump}→{Key:Key_NorAttack} để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_CresecentAura_3_LV1}.<br/><br/> Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 2]",
    "s062490": "Các đòn tấn công cường hóa Lôi có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_LightningStab_LV1#Storm Fang} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpLightning#Lightning}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element} Lv. 1 trở lên]",
    "s070785": "Nhấn {Key:Key_NorAttack} liên tục, {Key:Key_Roll}→{Key:Key_NorAttack}, hoặc {Key:Key_Jump}→{Key:Key_NorAttack} để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_PhantomStab_LV1}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 2]",
    "s073580": "Nhấn {Key:Key_Skill_6} để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_Praevus}.<br/>Tiêu hao thêm {StaticInfo:SubLevel:Stamina}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_SwordMastery_I} Lv. 2]",
    "s074703": "Nhấn {Key:Key_Guard} ngay trước khi bị đánh trúng để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_ImpBoss}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 1]",
    "s076792": "Các đòn tấn công cường hóa Hỏa có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_FireBreath_LV1#Volcanic Eruption} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpFire#Flame}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element} Lv. 1 trở lên]",
    "s077585": "Nhấn {Key:Key_Skill_6}để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_Forgotten_General}.<br/>Tiêu hao thêm {StaticInfo:SubLevel:Stamina}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_SwordMastery_I} Lv. 2]",
    "s084188": "Các đòn tấn công cường hóa Phong có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_Primus#Ancient Reckoning} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpWind#Wind}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element}: Lv. 1 trở lên]",
    "s085540": "Các đòn tấn công cường hóa Băng có thể kích hoạt {StaticInfo:Item:Item_Skill_AbyssGear_FrostDeath_LV1#Shattering Frost} với cái giá là tiêu hao thêm Tinh lực.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_MpIce#Frost}] [{StaticInfo:Knowledge:Knowledge_ElementalReinforce#Imbue Element}: Lv. 1 trở lên]",
    "s087081": "Nhấn {Key:Key_Skill_6} để  sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_SoulStrike_LV1}.<br/>Tiêu hao thêm {StaticInfo:SubLevel:Stamina}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_SwordMastery_I} Lv. 2]",
    "s090543": "Nhấn {Key:Key_Guard} ngay trước khi bị đánh trúng để sử dụng {StaticInfo:Item:Item_Skill_AbyssGear_Titan}.<br/><br/>Kỹ năng yêu cầu: [{StaticInfo:Knowledge:Knowledge_Nature} Lv. 1]",
}

for sid, text in updates.items():
    sid_to_vi[sid] = text

sid_path.write_text(json.dumps(sid_to_vi, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(updates))
