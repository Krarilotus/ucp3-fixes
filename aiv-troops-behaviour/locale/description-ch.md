# AI：AIV部队行为

恢复长枪兵和两种剑士缺失的AIV位置。可选设置控制全部15种部队的初始职责和防御移动。

按兵种选择防守或挖掘、驻守或巡逻。仅能挖掘的部队可选择挖掘。

为各AI设置`AIVTroops_InitialRole_<Troop>`（`"defend"` / `"dig"`）和`AIVTroops_Movement_<Troop>`（`"hold"` / `"patrol"`）。去掉兵种后缀即为该AI的通用设置；通用职责仅接受`"defend"`。启用的AIC覆盖优先；省略的字段继承默认值。

示例：`AIVTroops_InitialRole_Slave: "dig"`将奴隶分配为挖掘部队。兵种名和详细说明见[AIC字段参考](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour)。

部队设置初始为关闭。修改后重启游戏并开始新对局。
