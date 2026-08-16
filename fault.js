import {k as I, a as T, m as M, n as W, i as t, u as Ft, _ as nt} from "./index-DFatz3Ak.js";
import {d as wt, r as w, c as U, f as Lt, w as Rt, o as bt, M as j, z as L, N as v, y as d, X as c, V as r, A as u, W as o, x as y, h as N, u as R, a_ as ct, $ as b, a$ as K, G as A, K as X} from "./antv-CToMIxBj.js";
import "./vue-echarts-C46CWUzL.js";
const mt = {
    1: t.global.t("views.FaultReportList.62pav1iy6xg0"),
    2: t.global.t("views.FaultReportList.62pav1iy72g0"),
    3: t.global.t("views.FaultReportList.62pav1iy7480")
}
  , dt = Object.freeze({
    门禁1告警: t.global.t("views.FaultReportList.Access Control 1 Alarm"),
    门禁2告警: t.global.t("views.FaultReportList.Access Control 2 Alarm"),
    水浸1告警: t.global.t("views.FaultReportList.Water Immersion 1 Alarm"),
    水浸2告警: t.global.t("views.FaultReportList.Water Immersion 2 Alarm"),
    频率异常: t.global.t("views.FaultReportList.frequency"),
    失压: t.global.t("views.FaultReportList.voltage"),
    一级设备离线: t.global.t("views.FaultReportList.offline"),
    "通信故障/离线": t.global.t("views.FaultReportList.communicationFault"),
    北向通信故障: t.global.t("views.FaultReportList.northboundFault"),
    逆流警报: t.global.t("views.FaultReportList.countercurrentAlarm"),
    需量警报: t.global.t("views.FaultReportList.demandAlarm"),
    设备断电告警: t.global.t("views.FaultReportList.equipmentAlarm"),
    EPO故障: t.global.t("views.FaultReportList.EPO Fault"),
    "IGBT OCP故障": t.global.t("views.FaultReportList.IGBT OCP Fault"),
    高压侧硬件过压故障: t.global.t("views.FaultReportList.High Voltage Side Hardware Overvoltage Fault"),
    高压侧硬件过流故障: t.global.t("views.FaultReportList.High Voltage Side Hardware Overcurrent Fault"),
    "IGBT 硬件过流故障": t.global.t("views.FaultReportList.IGBT Hardware Overcurrent Fault"),
    "24V辅助电源故障": t.global.t("views.FaultReportList.24V Auxiliary Power Fault"),
    风扇故障: t.global.t("views.FaultReportList.Fan Fault"),
    单板连接故障: t.global.t("views.FaultReportList.Single Board Connection Fault"),
    功率模块过温: t.global.t("views.FaultReportList.Power Module Overtemperature"),
    "±15V辅助电源故障": t.global.t("views.FaultReportList.±15V Auxiliary Power Fault"),
    预充电超时故障: t.global.t("views.FaultReportList.Precharge Timeout Fault"),
    "低压侧 A 相软件过流故障": t.global.t("views.FaultReportList.Low Voltage Side Phase A Software Overcurrent Fault"),
    "低压侧 B 相软件过流故障": t.global.t("views.FaultReportList.Low Voltage Side Phase B Software Overcurrent Fault"),
    "低压侧 C 相软件过流故障": t.global.t("views.FaultReportList.Low Voltage Side Phase C Software Overcurrent Fault"),
    低压侧负端软件过流故障: t.global.t("views.FaultReportList.Low Voltage Side Negative Terminal Software Overcurrent Fault"),
    模块内部短路故障: t.global.t("views.FaultReportList.Module Internal Short Circuit Fault"),
    高压侧预充过压故障: t.global.t("views.FaultReportList.High Voltage Side Precharge Overvoltage Fault"),
    高压侧极性反接故障: t.global.t("views.FaultReportList.High Voltage Side Polarity Reverse Fault"),
    高压侧短路故障: t.global.t("views.FaultReportList.High Voltage Side Short Circuit Fault"),
    高压侧运行过压故障: t.global.t("views.FaultReportList.High Voltage Side Operation Overvoltage Fault"),
    高压侧运行欠压故障: t.global.t("views.FaultReportList.High Voltage Side Operation Undervoltage Fault"),
    高压侧正负母线不平衡故障: t.global.t("views.FaultReportList.High Voltage Side Positive Negative Bus Imbalance Fault"),
    与主机模式设置不匹配: t.global.t("views.FaultReportList.Mode Setting Mismatch with Host"),
    "控制板 EEROM 故障标志位": t.global.t("views.FaultReportList.Control Board EEPROM Fault Flag"),
    "从机 CAN 通信故障标志位": t.global.t("views.FaultReportList.Slave CAN Communication Fault Flag"),
    "与 EMS 通信故障标志位": t.global.t("views.FaultReportList.EMS Communication Fault Flag"),
    绝缘电阻过低故障: t.global.t("views.FaultReportList.Insulation Resistance Too Low Fault"),
    低压侧欠压故障: t.global.t("views.FaultReportList.Low Voltage Side Undervoltage Fault"),
    软件瞬态过流故障: t.global.t("views.FaultReportList.Software Transient Overcurrent Fault"),
    低压侧过压故障: t.global.t("views.FaultReportList.Low Voltage Side Overvoltage Fault"),
    低压侧过流故障: t.global.t("views.FaultReportList.Low Voltage Side Overcurrent Fault"),
    低压侧极性反接故障: t.global.t("views.FaultReportList.Low Voltage Side Polarity Reverse Fault"),
    门禁报警: t.global.t("views.FaultReportList.Access Control Alarm"),
    水浸报警: t.global.t("views.FaultReportList.Water Immersion Alarm"),
    消防告警: t.global.t("views.FaultReportList.Fire Alarm"),
    "EPO 故障标志": t.global.t("views.FaultReportList.EPO Fault Flag"),
    "IGBT 硬件过流标志": t.global.t("views.FaultReportList.IGBT Hardware Overcurrent Flag"),
    母线硬件过压标志: t.global.t("views.FaultReportList.Bus Hardware Overvoltage Flag"),
    功率模块逐波限流标志: t.global.t("views.FaultReportList.Power Module Wave-by-Wave Current Limit Flag"),
    平衡模块硬件过流标志: t.global.t("views.FaultReportList.Balance Module Hardware Overcurrent Flag"),
    "24V 电源故障标志": t.global.t("views.FaultReportList.24V Power Fault Flag"),
    风扇故障标志: t.global.t("views.FaultReportList.Fan Fault Flag"),
    连接故障标志: t.global.t("views.FaultReportList.Connection Fault Flag"),
    防雷器故障: t.global.t("views.FaultReportList.Surge Protector Fault"),
    电感过温故障标志: t.global.t("views.FaultReportList.Inductor Overtemperature Fault Flag"),
    功率模块过温标志: t.global.t("views.FaultReportList.Power Module Overtemperature Flag"),
    平衡模块过温标志: t.global.t("views.FaultReportList.Balance Module Overtemperature Flag"),
    "15V 电源故障标志": t.global.t("views.FaultReportList.15V Power Fault Flag"),
    系统火警故障标志: t.global.t("views.FaultReportList.System Fire Alarm Fault Flag"),
    电池干接点故障标志: t.global.t("views.FaultReportList.Battery Dry Contact Fault Flag"),
    干接点过载故障标志: t.global.t("views.FaultReportList.Dry Contact Overload Fault Flag"),
    环境温度过温故障标志: t.global.t("views.FaultReportList.Ambient Temperature Overtemperature Fault Flag"),
    干接点过温故障标志: t.global.t("views.FaultReportList.Dry Contact Overtemperature Fault Flag"),
    "A 相过压故障标志": t.global.t("views.FaultReportList.Phase A Overvoltage Fault Flag"),
    "B 相过压故障标志": t.global.t("views.FaultReportList.Phase B Overvoltage Fault Flag"),
    "C 相过压故障标志": t.global.t("views.FaultReportList.Phase C Overvoltage Fault Flag"),
    "A 相欠压故障标志": t.global.t("views.FaultReportList.Phase A Undervoltage Fault Flag"),
    "B 相欠压故障标志": t.global.t("views.FaultReportList.Phase B Undervoltage Fault Flag"),
    "C 相欠压故障标志": t.global.t("views.FaultReportList.Phase C Undervoltage Fault Flag"),
    电网过频: t.global.t("views.FaultReportList.Grid Overfrequency"),
    电网欠频: t.global.t("views.FaultReportList.Grid Underfrequency"),
    电网相序错误: t.global.t("views.FaultReportList.Grid Phase Sequence Error"),
    "A 相软件过流": t.global.t("views.FaultReportList.Phase A Software Overcurrent"),
    "B 相软件过流": t.global.t("views.FaultReportList.Phase B Software Overcurrent"),
    "C 相软件过流": t.global.t("views.FaultReportList.Phase C Software Overcurrent"),
    电网电压不平衡: t.global.t("views.FaultReportList.Grid Voltage Imbalance"),
    电网电流不平衡: t.global.t("views.FaultReportList.Grid Current Imbalance"),
    电网缺相: t.global.t("views.FaultReportList.Grid Phase Loss"),
    "N 线过流": t.global.t("views.FaultReportList.Neutral Line Overcurrent"),
    预充母线过压: t.global.t("views.FaultReportList.Precharge Bus Overvoltage"),
    预充母线欠压: t.global.t("views.FaultReportList.Precharge Bus Undervoltage"),
    不控整流母线过压: t.global.t("views.FaultReportList.Uncontrolled Rectifier Bus Overvoltage"),
    不控整流母线欠压: t.global.t("views.FaultReportList.Uncontrolled Rectifier Bus Undervoltage"),
    运行母线过压: t.global.t("views.FaultReportList.Operation Bus Overvoltage"),
    运行母线欠压: t.global.t("views.FaultReportList.Operation Bus Undervoltage"),
    正负母线不平衡: t.global.t("views.FaultReportList.Positive Negative Bus Imbalance"),
    电池欠压: t.global.t("views.FaultReportList.Battery Undervoltage"),
    电流模式母线欠压: t.global.t("views.FaultReportList.Current Mode Bus Undervoltage"),
    电池过压: t.global.t("views.FaultReportList.Battery Overvoltage"),
    直流预充电过流: t.global.t("views.FaultReportList.DC Precharge Overcurrent"),
    直流过流: t.global.t("views.FaultReportList.DC Overcurrent"),
    平衡模块软件过流: t.global.t("views.FaultReportList.Balance Module Software Overcurrent"),
    电池反接: t.global.t("views.FaultReportList.Battery Reverse Connection"),
    预充电超时: t.global.t("views.FaultReportList.Precharge Timeout"),
    "预充电 A 相过流": t.global.t("views.FaultReportList.Precharge Phase A Overcurrent"),
    "预充电 B 相过流": t.global.t("views.FaultReportList.Precharge Phase B Overcurrent"),
    "预充电 C 相过流": t.global.t("views.FaultReportList.Precharge Phase C Overcurrent"),
    "控制板 EEPROM 故障": t.global.t("views.FaultReportList.Control Board EEPROM Fault"),
    "AD 采样零漂故障": t.global.t("views.FaultReportList.AD Sampling Zero Drift Fault"),
    后台通讯协议故障: t.global.t("views.FaultReportList.Background Communication Protocol Fault"),
    绝缘检测故障: t.global.t("views.FaultReportList.Insulation Detection Fault"),
    "BMS 电池系统故障": t.global.t("views.FaultReportList.BMS Battery System Fault"),
    "STS 通信故障": t.global.t("views.FaultReportList.STS Communication Fault"),
    "BMS 通信故障": t.global.t("views.FaultReportList.BMS Communication Fault"),
    "从模块 CAN 通信故障": t.global.t("views.FaultReportList.Slave Module CAN Communication Fault"),
    "EMS 通信故障": t.global.t("views.FaultReportList.EMS Communication Fault"),
    预充电继电器闭合失败: t.global.t("views.FaultReportList.Precharge Relay Close Failure"),
    预充电继电器断开失败: t.global.t("views.FaultReportList.Precharge Relay Open Failure"),
    预充电继电器闭合状态错误: t.global.t("views.FaultReportList.Precharge Relay Close Status Error"),
    预充电继电器断开状态错误: t.global.t("views.FaultReportList.Precharge Relay Open Status Error"),
    主继电器闭合失败: t.global.t("views.FaultReportList.Main Relay Close Failure"),
    主继电器断开失败: t.global.t("views.FaultReportList.Main Relay Open Failure"),
    主继电器闭合状态错误: t.global.t("views.FaultReportList.Main Relay Close Status Error"),
    主继电器断开状态错误: t.global.t("views.FaultReportList.Main Relay Open Status Error"),
    交流主继电器粘连故障: t.global.t("views.FaultReportList.AC Main Relay Sticking Fault"),
    直流继电器开路故障: t.global.t("views.FaultReportList.DC Relay Open Circuit Fault"),
    "逆变电压 A 相过压故障标志": t.global.t("views.FaultReportList.Inverter Voltage Phase A Overvoltage Fault Flag"),
    "逆变电压 B 相过压故障标志": t.global.t("views.FaultReportList.Inverter Voltage Phase B Overvoltage Fault Flag"),
    "逆变电压 C 相过压故障标志": t.global.t("views.FaultReportList.Inverter Voltage Phase C Overvoltage Fault Flag"),
    电网孤岛故障标志: t.global.t("views.FaultReportList.Grid Islanding Fault Flag"),
    系统谐振故障标志: t.global.t("views.FaultReportList.System Resonance Fault Flag"),
    软件过压过流标志: t.global.t("views.FaultReportList.Software Overvoltage Overcurrent Flag"),
    高电压穿越超时故障标志: t.global.t("views.FaultReportList.High Voltage Ride Through Timeout Fault Flag"),
    "逆变电压 A 相欠压故障标志": t.global.t("views.FaultReportList.Inverter Voltage Phase A Undervoltage Fault Flag"),
    "逆变电压 B 相欠压故障标志": t.global.t("views.FaultReportList.Inverter Voltage Phase B Undervoltage Fault Flag"),
    "逆变电压 C 相欠压故障标志": t.global.t("views.FaultReportList.Inverter Voltage Phase C Undervoltage Fault Flag"),
    离网无同步信号故障标志: t.global.t("views.FaultReportList.Off-grid No Synchronization Signal Fault Flag"),
    离网短路故障标志: t.global.t("views.FaultReportList.Off-grid Short Circuit Fault Flag"),
    低电压穿越超时故障标志: t.global.t("views.FaultReportList.Low Voltage Ride Through Timeout Fault Flag"),
    BMU硬件故障: t.global.t("views.FaultReportList.BMU Hardware Fault"),
    BCU硬件故障: t.global.t("views.FaultReportList.BCU Hardware Fault"),
    接触器粘连故障: t.global.t("views.FaultReportList.Contactor Sticking Fault"),
    总压差过大: t.global.t("views.FaultReportList.Total Voltage Difference Too High"),
    绝缘过低: t.global.t("views.FaultReportList.Insulation Too Low"),
    单体电压过高: t.global.t("views.FaultReportList.Cell Voltage Too High"),
    单体温度过高: t.global.t("views.FaultReportList.Cell Temperature Too High"),
    单体电压更新异常: t.global.t("views.FaultReportList.Cell Voltage Update Abnormal"),
    极柱温度过高: t.global.t("views.FaultReportList.Terminal Temperature Too High"),
    放电电流过大: t.global.t("views.FaultReportList.Discharge Current Too High"),
    绝缘监测故障: t.global.t("views.FaultReportList.Insulation Monitoring Fault"),
    电池NTC故障: t.global.t("views.FaultReportList.Battery NTC Fault"),
    端子NTC故障: t.global.t("views.FaultReportList.Terminal NTC Fault"),
    电池温度故障: t.global.t("views.FaultReportList.Battery Temperature Fault"),
    单体电压采样故障: t.global.t("views.FaultReportList.Cell Voltage Sampling Fault"),
    采样芯片故障: t.global.t("views.FaultReportList.Sampling Chip Fault"),
    电流采样故障: t.global.t("views.FaultReportList.Current Sampling Fault"),
    单体电压过低: t.global.t("views.FaultReportList.Cell Voltage Too Low"),
    充电电流过大: t.global.t("views.FaultReportList.Charge Current Too High"),
    BMU自检: t.global.t("views.FaultReportList.BMU Self-check"),
    BCU自检: t.global.t("views.FaultReportList.BCU Self-check"),
    熔断器故障: t.global.t("views.FaultReportList.Fuse Fault"),
    接触器故障: t.global.t("views.FaultReportList.Contactor Fault"),
    BMU通信故障: t.global.t("views.FaultReportList.BMU Communication Fault"),
    BAU通信故障: t.global.t("views.FaultReportList.BAU Communication Fault"),
    电流传感器故障: t.global.t("views.FaultReportList.Current Sensor Fault"),
    电压传感器故障: t.global.t("views.FaultReportList.Voltage Sensor Fault"),
    绝缘监测设备故障: t.global.t("views.FaultReportList.Insulation Monitoring Device Fault"),
    隔开开关异常断开: t.global.t("views.FaultReportList.Isolation Switch Abnormal Open"),
    NTC故障: t.global.t("views.FaultReportList.NTC Fault"),
    PCS通信故障: t.global.t("views.FaultReportList.PCS Communication Fault"),
    总电压过压一级报警: t.global.t("views.FaultReportList.Total Voltage Overvoltage Level 1 Alarm"),
    总电压欠压一级报警: t.global.t("views.FaultReportList.Total Voltage Undervoltage Level 1 Alarm"),
    SOC低一级报警: t.global.t("views.FaultReportList.SOC Level-1 Alarm"),
    SOC低二级级报警: t.global.t("views.FaultReportList.SOC Level-2 Alarm"),
    SOC低三级级报警: t.global.t("views.FaultReportList.SOC Level-3 Alarm"),
    "BMS 通讯故障": t.global.t("views.FaultReportList.BMS Communication Fault"),
    "PCS 通讯故障": t.global.t("views.FaultReportList.PCS Communication Fault"),
    单体过压一级报警: t.global.t("views.FaultReportList.Cell Overvoltage Level 1 Alarm"),
    单体欠压一级报警: t.global.t("views.FaultReportList.Cell Undervoltage Level 1 Alarm"),
    放电电流过大一级报警: t.global.t("views.FaultReportList.Discharge Current Too High Level 1 Alarm"),
    充电电流过大一级报警: t.global.t("views.FaultReportList.Charge Current Too High Level 1 Alarm"),
    放电电池过温一级报警: t.global.t("views.FaultReportList.Discharge Battery Overtemperature Level 1 Alarm"),
    放电电池欠温一级报警: t.global.t("views.FaultReportList.Discharge Battery Undertemperature Level 1 Alarm"),
    充电电池过温一级报警: t.global.t("views.FaultReportList.Charge Battery Overtemperature Level 1 Alarm"),
    充电电池欠温一级报警: t.global.t("views.FaultReportList.Charge Battery Undertemperature Level 1 Alarm"),
    绝缘阻值过低一级报警: t.global.t("views.FaultReportList.Insulation Resistance Too Low Level 1 Alarm"),
    极柱温度过高一级报警: t.global.t("views.FaultReportList.Terminal Temperature Too High Level 1 Alarm"),
    高压箱连接器温度过高一级报警: t.global.t("views.FaultReportList.High Voltage Box Connector Temperature Too High Level 1 Alarm"),
    单体压差一级报警: t.global.t("views.FaultReportList.Cell Voltage Difference Level 1 Alarm"),
    单体温差一级报警: t.global.t("views.FaultReportList.Cell Temperature Difference Level 1 Alarm"),
    "SOC 低一级报警": t.global.t("views.FaultReportList.SOC Low Level 1 Alarm"),
    总电压过压二级报警: t.global.t("views.FaultReportList.Total Voltage Overvoltage Level 2 Alarm"),
    总电压欠压二级报警: t.global.t("views.FaultReportList.Total Voltage Undervoltage Level 2 Alarm"),
    单体过压二级报警: t.global.t("views.FaultReportList.Cell Overvoltage Level 2 Alarm"),
    单体欠压二级报警: t.global.t("views.FaultReportList.Cell Undervoltage Level 2 Alarm"),
    放电电流过大二级报警: t.global.t("views.FaultReportList.Discharge Current Too High Level 2 Alarm"),
    充电电流过大二级报警: t.global.t("views.FaultReportList.Charge Current Too High Level 2 Alarm"),
    放电电池过温二级报警: t.global.t("views.FaultReportList.Discharge Battery Overtemperature Level 2 Alarm"),
    放电电池欠温二级报警: t.global.t("views.FaultReportList.Discharge Battery Undertemperature Level 2 Alarm"),
    充电电池过温二级报警: t.global.t("views.FaultReportList.Charge Battery Overtemperature Level 2 Alarm"),
    充电电池欠温二级报警: t.global.t("views.FaultReportList.Charge Battery Undertemperature Level 2 Alarm"),
    绝缘阻值过低二级报警: t.global.t("views.FaultReportList.Insulation Resistance Too Low Level 2 Alarm"),
    极柱温度过高二级报警: t.global.t("views.FaultReportList.Terminal Temperature Too High Level 2 Alarm"),
    高压箱连接器温度过高二级报警: t.global.t("views.FaultReportList.High Voltage Box Connector Temperature Too High Level 2 Alarm"),
    单体压差二级报警: t.global.t("views.FaultReportList.Cell Voltage Difference Level 2 Alarm"),
    单体温差二级报警: t.global.t("views.FaultReportList.Cell Temperature Difference Level 2 Alarm"),
    SOC低二级报警: t.global.t("views.FaultReportList.SOC Low Level 2 Alarm"),
    总电压过压三级报警: t.global.t("views.FaultReportList.Total Voltage Overvoltage Level 3 Alarm"),
    总电压欠压三级报警: t.global.t("views.FaultReportList.Total Voltage Undervoltage Level 3 Alarm"),
    单体过压三级报警: t.global.t("views.FaultReportList.Cell Overvoltage Level 3 Alarm"),
    单体欠压三级报警: t.global.t("views.FaultReportList.Cell Undervoltage Level 3 Alarm"),
    放电电流过大三级报警: t.global.t("views.FaultReportList.Discharge Current Too High Level 3 Alarm"),
    充电电流过大三级报警: t.global.t("views.FaultReportList.Charge Current Too High Level 3 Alarm"),
    放电电池过温三级报警: t.global.t("views.FaultReportList.Discharge Battery Overtemperature Level 3 Alarm"),
    放电电池欠温三级报警: t.global.t("views.FaultReportList.Discharge Battery Undertemperature Level 3 Alarm"),
    充电电池过温三级报警: t.global.t("views.FaultReportList.Charge Battery Overtemperature Level 3 Alarm"),
    充电电池欠温三级报警: t.global.t("views.FaultReportList.Charge Battery Undertemperature Level 3 Alarm"),
    绝缘阻值过低三级报警: t.global.t("views.FaultReportList.Insulation Resistance Too Low Level 3 Alarm"),
    极柱温度过高三级报警: t.global.t("views.FaultReportList.Terminal Temperature Too High Level 3 Alarm"),
    高压箱连接器温度过高三级报警: t.global.t("views.FaultReportList.High Voltage Box Connector Temperature Too High Level 3 Alarm"),
    单体压差三级报警: t.global.t("views.FaultReportList.Cell Voltage Difference Level 3 Alarm"),
    单体温差三级报警: t.global.t("views.FaultReportList.Cell Temperature Difference Level 3 Alarm"),
    SOC低三级报警: t.global.t("views.FaultReportList.SOC Low Level 3 Alarm")
})
  , yt = Object.freeze({
    未知: t.global.t("views.FaultReportList.unknown"),
    辅控: t.global.t("views.FaultReportList.AuxiliaryControl"),
    电表: t.global.t("views.FaultReportList.ElectricMeter"),
    风冷: t.global.t("views.FaultReportList.AirCooling"),
    液冷: t.global.t("views.FaultReportList.LiquidCooling"),
    消防: t.global.t("views.FaultReportList.FireProtection"),
    压力: t.global.t("views.FaultReportList.Pressure"),
    逆变: t.global.t("views.FaultReportList.Inversion"),
    逆变器: t.global.t("views.FaultReportList.Inverter"),
    电池: t.global.t("views.FaultReportList.Battery")
})
  , Ct = {
    key: 0,
    class: "warning-statics"
}
  , ht = {
    class: "current-warpper-left public-style"
}
  , St = {
    class: "current-warpper-center public-style"
}
  , At = {
    class: "current-warpper-right public-style"
}
  , Ot = {
    key: 1,
    class: "warning-statics"
}
  , Tt = {
    class: "current-warpper-left public-style"
}
  , Bt = {
    class: "current-warpper-center public-style"
}
  , ft = {
    class: "current-warpper-right public-style"
}
  , Pt = {
    style: {
        "margin-left": "10px"
    }
}
  , Vt = {
    class: "search-list"
}
  , Nt = nt(wt({
    __name: "FaultReportList",
    setup(kt) {
        const {t: i} = Ft();
        let m = w(!1);
        const D = w(0)
          , g = w("1")
          , F = w(1)
          , p = w(10);
        w(!1);
        const x = w([])
          , B = w()
          , f = w()
          , P = w(!1)
          , Z = U( () => t.global.locale.value === "zh-cn")
          , J = [{
            label: i("views.FaultReportList.62pav1iy6tk0"),
            value: ""
        }, {
            label: "ems",
            value: "ems"
        }, {
            label: "elec",
            value: "elec"
        }]
          , Q = [{
            label: i("views.FaultReportList.62pav1iy6vg0"),
            value: ""
        }, {
            label: i("views.FaultReportList.62pav1iy6xg0"),
            value: 1
        }, {
            label: i("views.FaultReportList.62pav1iy72g0"),
            value: 2
        }, {
            label: i("views.FaultReportList.62pav1iy7480"),
            value: 3
        }]
          , l = Lt({
            search: "",
            level: "",
            alarmType: ""
        });
        Rt(l, async e => {
            await C({
                ...e,
                level: Number(e.level),
                page: F.value,
                pageSize: p.value,
                handleStatus: Number(g.value)
            })
        }
        );
        const tt = async () => {
            await C({
                ...l,
                level: Number(l.level),
                page: F.value,
                pageSize: p.value,
                handleStatus: Number(g.value)
            })
        }
          , et = () => {
            l.alarmType = "",
            l.level = "",
            l.search = ""
        }
          , lt = U( () => ({
            total: D.value,
            current: F.value,
            pageSize: p.value,
            onChange: async (e, a) => {
                await C({
                    page: e,
                    pageSize: a,
                    ...l,
                    level: Number(l.level),
                    handleStatus: Number(g.value)
                }),
                p.value = a,
                F.value = e
            }
        }))
          , at = [{
            key: "1",
            tab: i("views.FaultReportList.62pav1iy5lc0")
        }, {
            key: "2",
            tab: i("views.FaultReportList.62pav1iy7680")
        }]
          , E = [{
            title: i("views.FaultReportList.62pav1iy7800"),
            dataIndex: "index",
            align: "center",
            key: "index",
            customRender: (e, a, O) => `${O + 1}`
        }, {
            title: i("views.FaultReportList.62pav1iy79s0"),
            dataIndex: "content",
            key: "content"
        }, {
            title: i("views.FaultReportList.62pav1iy7bo0"),
            key: "level",
            dataIndex: "level"
        }, {
            title: i("views.FaultReportList.62pav1iy7gw0"),
            key: "alarmType",
            dataIndex: "alarmType"
        }, {
            title: i("views.FaultReportList.62pav1iy7io0"),
            key: "deviceType",
            dataIndex: "deviceType"
        }, {
            title: i("views.FaultReportList.62pav1iy7kw0"),
            key: "deviceName",
            dataIndex: "deviceName"
        }, {
            title: i("views.FaultReportList.62pav1iy7ms0"),
            key: "deviceId",
            dataIndex: "deviceId"
        }, {
            title: i("views.FaultReportList.62pav1iy7o80"),
            key: "occurTime",
            dataIndex: "occurTime"
        }]
          , ot = U( () => g.value === "1" ? [...E, {
            title: i("views.FaultReportList.62pav1iy7ps0"),
            key: "action"
        }] : [...E, {
            title: i("views.FaultReportList.62pav1iy7rg0"),
            key: "handleTime",
            dataIndex: "handleTime"
        }])
          , rt = async () => {
            try {
                P.value = !0,
                await (async () => await W(`${T}/v1/alarm/batch-handle`, {}))(),
                P.value = !1,
                await C({
                    page: 1,
                    pageSize: p.value,
                    ...l,
                    level: Number(l.level),
                    handleStatus: Number(g.value)
                })
            } catch {
                P.value = !1
            }
        }
          , it = async e => {
            m.value = !0;
            try {
                await (async a => await W(`${T}/v1/alarm/${a}`, {}))(e),
                m.value = !1,
                await C({
                    ...l,
                    level: Number(l.level),
                    page: F.value,
                    pageSize: p.value,
                    handleStatus: Number(g.value)
                })
            } catch {
                m.value = !1
            }
        }
          , C = async e => {
            m.value = !0;
            try {
                const a = await (async O => {
                    const h = await I(`${T}/v1/alarm`, O);
                    return M.toCamelcase(h)
                }
                )(e);
                x.value = a.data.list,
                D.value = a.data.total,
                m.value = !1
            } catch {
                m.value = !1
            }
        }
          , $ = async () => {
            const e = await (async () => {
                const a = await I(`${T}/v1/alarm/current`);
                return M.toCamelcase(a)
            }
            )();
            B.value = e.data
        }
          , st = async () => {
            const e = await (async () => {
                const a = await I(`${T}/v1/alarm/history`);
                return M.toCamelcase(a)
            }
            )();
            f.value = e.data
        }
        ;
        return bt(async () => {
            await $(),
            await C({
                ...l,
                level: Number(l.level),
                page: F.value,
                pageSize: p.value,
                handleStatus: Number(g.value)
            })
        }
        ),
        (e, a) => {
            const O = y("a-input")
              , h = y("a-form-item")
              , _ = y("a-select")
              , V = y("a-button")
              , ut = y("a-form")
              , vt = y("a-space")
              , gt = y("a-table")
              , pt = y("a-card");
            return L(),
            j(pt, {
                style: {
                    width: "100%",
                    height: "100%",
                    "overflow-y": "auto"
                },
                "tab-list": at,
                "active-tab-key": g.value,
                onTabChange: a[3] || (a[3] = k => (async S => {
                    g.value = S,
                    S === "1" ? await $() : await st(),
                    await C({
                        ...l,
                        level: Number(l.level),
                        page: 1,
                        pageSize: p.value,
                        handleStatus: Number(S)
                    }),
                    F.value = 1
                }
                )(k))
            }, {
                default: v( () => {
                    var k, S, G, z, Y, q;
                    return [g.value === "1" ? (L(),
                    d("div", Ct, [r("div", ht, [r("p", null, o(e.$t("views.FaultReportList.62pav1iy5lc0")), 1), r("h4", null, o((k = B.value) == null ? void 0 : k.currentAlarmCount), 1)]), r("div", St, [r("p", null, o(e.$t("views.FaultReportList.62pav1iy6840")), 1), r("h4", null, o((S = B.value) == null ? void 0 : S.todayNewAlarmCount), 1)]), r("div", At, [r("p", null, o(e.$t("views.FaultReportList.62pav1iy6aw0")), 1), r("h4", null, o((G = B.value) == null ? void 0 : G.sevenBeforeAlarmCount), 1)])])) : c("", !0), g.value === "2" ? (L(),
                    d("div", Ot, [r("div", Tt, [r("p", null, o(e.$t("views.FaultReportList.62pav1iy6cw0")), 1), r("h4", null, o((z = f.value) == null ? void 0 : z.historyAlarmCount), 1)]), r("div", Bt, [r("p", null, o(e.$t("views.FaultReportList.62pav1iy6ew0")), 1), r("h4", null, o((Y = f.value) == null ? void 0 : Y.todayHandleAlarmCount), 1)]), r("div", ft, [r("p", null, o(e.$t("views.FaultReportList.62pav1iy6h40")), 1), r("h4", null, o((q = f.value) == null ? void 0 : q.aveHandleTime), 1), r("p", Pt, o(e.$t("views.FaultReportList.62pav1iy6j40")), 1)])])) : c("", !0), r("div", Vt, [u(ut, {
                        layout: "inline",
                        model: l
                    }, {
                        default: v( () => [u(h, null, {
                            default: v( () => [u(O, {
                                value: l.search,
                                "onUpdate:value": a[0] || (a[0] = s => l.search = s),
                                placeholder: e.$t("views.FaultReportList.62pav1iy6l00")
                            }, null, 8, ["value", "placeholder"])]),
                            _: 1
                        }), u(h, null, {
                            default: v( () => [u(_, {
                                options: Q,
                                value: l.level,
                                "onUpdate:value": a[1] || (a[1] = s => l.level = s)
                            }, null, 8, ["value"])]),
                            _: 1
                        }), u(h, null, {
                            default: v( () => [u(_, {
                                options: J,
                                value: l.alarmType,
                                "onUpdate:value": a[2] || (a[2] = s => l.alarmType = s)
                            }, null, 8, ["value"])]),
                            _: 1
                        }), u(h, null, {
                            default: v( () => [u(V, {
                                style: {
                                    background: "#142f5e"
                                },
                                onClick: et,
                                type: "primary",
                                icon: N(R(ct))
                            }, {
                                default: v( () => [b(o(e.$t("views.FaultReportList.62pav1iy6nc0")), 1)]),
                                _: 1
                            }, 8, ["icon"])]),
                            _: 1
                        })]),
                        _: 1
                    }, 8, ["model"]), u(vt, null, {
                        default: v( () => [u(V, {
                            loading: P.value,
                            onClick: rt,
                            type: "primary",
                            icon: N(R(K))
                        }, {
                            default: v( () => [b(o(e.$t("views.FaultReportList.69ggak3tg7s0")), 1)]),
                            _: 1
                        }, 8, ["loading", "icon"]), u(V, {
                            onClick: tt,
                            type: "text",
                            icon: N(R(K))
                        }, {
                            default: v( () => [b(o(e.$t("views.FaultReportList.62pav1iy6ps0")), 1)]),
                            _: 1
                        }, 8, ["icon"])]),
                        _: 1
                    })]), u(gt, {
                        loading: R(m),
                        pagination: lt.value,
                        columns: ot.value,
                        dataSource: x.value,
                        bordered: !1,
                        rowKey: (s, n) => n
                    }, {
                        bodyCell: v( ({column: s, record: n, index: H}) => [s.key === "index" ? (L(),
                        d(A, {
                            key: 0
                        }, [b(o(H + 1 + p.value * (F.value - 1) >= 10 ? H + 1 + p.value * (F.value - 1) : `0${H + 1 + p.value * (F.value - 1)}`), 1)], 64)) : c("", !0), s.key === "level" ? (L(),
                        d(A, {
                            key: 1
                        }, [b(o(R(mt)[n.level]), 1)], 64)) : c("", !0), s.key === "handleTime" ? (L(),
                        d(A, {
                            key: 2
                        }, [b(o(R(X)(n.handleTime).utc().local().format("YYYY-MM-DD HH:mm:ss")), 1)], 64)) : c("", !0), s.key === "occurTime" ? (L(),
                        d(A, {
                            key: 3
                        }, [b(o(R(X)(n.occurTime).utc().local().format("YYYY-MM-DD HH:mm:ss")), 1)], 64)) : c("", !0), s.key === "deviceType" ? (L(),
                        d(A, {
                            key: 4
                        }, [b(o(R(yt)[n.deviceType] || n.deviceType), 1)], 64)) : c("", !0), s.key === "content" ? (L(),
                        d(A, {
                            key: 5
                        }, [b(o(Z.value ? n.content : R(dt)[n.content]), 1)], 64)) : c("", !0), s.key === "action" ? (L(),
                        j(V, {
                            key: 6,
                            onClick: Ht => it(n.id),
                            type: "primary",
                            loading: R(m)
                        }, {
                            default: v( () => [b(o(e.$t("views.FaultReportList.62pav1iy6rk0")), 1)]),
                            _: 2
                        }, 1032, ["onClick", "loading"])) : c("", !0)]),
                        _: 1
                    }, 8, ["loading", "pagination", "columns", "dataSource", "rowKey"])]
                }
                ),
                _: 1
            }, 8, ["active-tab-key"])
        }
    }
}), [["__scopeId", "data-v-48dafc74"]]);
export {Nt as default};
