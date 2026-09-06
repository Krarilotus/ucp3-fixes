# AI：AIV部队行为

恢复长枪兵和两种剑士缺失的AIV位置。可选设置控制全部15种部队的初始职责和防御移动。

每种部队的每组选项最多选一项。防守：前往AIV位置；挖掘：将初始部队分配为护城河挖掘单位。驻守：留在防御位置；巡逻：按照该AI的AIC巡逻设置在防御位置之间移动。再次点击已勾选的方框可清空该组选择，使用游戏默认行为。

为各AI设置`AIVTroops_InitialRole_<Troop>`（`"defend"` / `"dig"`）和`AIVTroops_Movement_<Troop>`（`"hold"` / `"patrol"`）。去掉兵种后缀即为该AI的通用设置；通用职责仅接受`"defend"`。启用的AIC覆盖优先；省略的字段继承默认值。

示例：`AIVTroops_InitialRole_Slave: "dig"`将奴隶分配为挖掘部队。兵种名和详细说明见[AIC字段参考](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour)。

部队设置初始为关闭。修改后重启游戏并开始新对局。
