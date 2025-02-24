"""
一、工具包导入
"""
from atrader import *
import numpy as np

"""
二、初始化
"""
def init(context):
    # 注册数据
    reg_kdata('day', 1)                         # 注册日频行情数据
    # 回测细节设置
    set_backtest(initial_cash=1e8)             # 初始化设置账户总资金
    # 全局变量定义/参数定义
    context.initial = 1e8
    context.win = 11                            # 计算所需总数据长度
    context.k1 = 0.4                           # 上轨参数参数
    context.k2 = 0.4                           # 下轨参数参数
    context.add = 0.005                             # 加仓参数
    context.Tlen = len(context.target_list)     # 标的数量
    context.record_entryP = np.array(np.zeros(context.Tlen))     # 记录入场点位
    context.future_info = get_future_info(context.target_list)   # 获取期货标的基本信息
"""
三、策略运行逻辑函数
"""
def on_data(context):
    # 获取注册数据
    data = get_reg_kdata(reg_idx=context.reg_kdata[0], length=context.win, fill_up=True, df=True)  # 所有标的的K线行情数据
    if data['close'].isna().any():               # 行情数据若存在nan值，则跳过
        return
    # 仓位数据查询
    long_positions = context.account().positions['volume_long']      # 获取多头仓位数据
    short_positions = context.account().positions['volume_short']    # 获取空头仓位数据
    # 时间计算
    bar_info = get_current_bar([0])               # 获取当前bar的信息
    bartime = bar_info.iloc[0, 1]                  # 获取当前bar的时间信息
    nowtime = bartime.hour * 100 + bartime.minute
    ##获取数据信息
    close = data.close.values.reshape(-1, context.win).astype(float)   # 获取收盘价，并转为ndarray类型的二维数组
    high = data.high.values.reshape(-1, context.win).astype(float)     # 获取最高价，并转为ndarray类型的二维数组
    low = data.low.values.reshape(-1, context.win).astype(float)       # 获取最低价，并转为ndarray类型的二维数组
    open = data.open.values.reshape(-1, context.win).astype(float)     # 获取开盘价，并转为ndarray类型的二维数组
  
    if (nowtime >= 1455) & (nowtime < 1500):
        if (long_positions.any() != 0)|(short_positions.any() != 0):
            order_close_all()  # 日内平仓
            return
    # print(nowtime)
    
    # 逻辑计算
    for i in range(context.Tlen):
        TR=[]
        for j in range(10):
            TodyHigh=high[i,j+1]-low[i,j+1]
            Eve1=abs(close[i,-11+j]-high[i,j+1])
            Eve2=abs(close[i,-11+j]-low[i,j+1])
            TR = TR+[max(TodyHigh,Eve1,Eve2)]                  # 波动范围
        ATR=np.mean(TR)
        # 每次要买入的仓位
        min_move = context.future_info['min_move'][i]                           # 标的最小变动单位
        Unit = context.initial * 0.01 / (ATR * min_move) / context.Tlen           # 标的每次买入仓位
        
        
        # 计算通道的上下轨
        Midline = get_EMA(close[i,-context.win:],11)[-1]
        Buyline = Midline + context.k1 * ATR
        Sellline = Midline - context.k2 * ATR
        # print(i,close[i,:])
        # print(i,' ',Buyline,'\n',close,'\n',Sellline,'\n\n')
        # 下单交易  
        if (long_positions[i] == 0) & (short_positions[i] == 0):    # 无持仓
            if close[i,-1] > Buyline:                           # 多单进场
                order_target_value(account_idx=0, target_idx=i, target_value=1e8/context.Tlen, side=1, order_type=2) # 多头下单
                context.record_entryP[i] = close[i,-1]              # 记录进场价格
                
            elif close[i,-1] < Sellline:                        # 空单进场
                order_target_value(account_idx=0, target_idx=i, target_value=1e8/context.Tlen, side=2, order_type=2) # 空头下单
                context.record_entryP[i] = close[i,-1]             # 记录进场价格


        elif long_positions[i] > 0:                 # 持有多头
            if close[i, -1] > context.record_entryP[i] + 3 * ATR:                # 多单加仓
                order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=1, order_type=2)
                context.record_entryP[i] = close[i, -1]            # 记录进场价格
                
            elif close[i,-1] < Midline:                         # 多单平仓
                order_target_value(account_idx=0, target_idx=i, target_value=0, side=1, order_type=2)
                context.record_entryP[i] = 0    
                
            elif close[i,-1] < context.record_entryP[i] - 4 * ATR:                  # 多单止损
                order_target_value(account_idx=0, target_idx=i, target_value=0, side=1, order_type=2)
                context.record_entryP[i] = 0
                    
                
        elif short_positions[i] > 0:                # 持有空头
            if close[i,-1] <  context.record_entryP[i] - 2.5 * ATR :               # 空单加仓
                order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=2, order_type=2)
                context.record_entryP[i] = close[i, -1]            # 记录进场价格
                
            elif close[i,-1] > Midline:                         # 空单平仓
                order_target_value(account_idx=0, target_idx=i, target_value=0, side=2, order_type=2)
                context.record_entryP[i] = 0     
                
            elif close[i,-1] > context.record_entryP[i] + 0.5 * ATR:                  # 空单止损
                order_target_value(account_idx=0, target_idx=i, target_value=0, side=2, order_type=2)
                context.record_entryP[i] = 0

"""
四、策略执行脚本
"""
if __name__ == '__main__':
    target_list = ['SHFE.zn0000', 'SHFE.rb0000']  # 设置回测标的

    # 策略回测函数begin_date='2019-01-01', end_date='2022-06-30' begin_date='2020-01-01', end_date='2021-01-01'
    run_backtest(strategy_name='ATR', file_path=r'E:\users\onedrive\桌面\ATR.py', target_list=target_list,
                 frequency='min', fre_num=5, begin_date='2019-01-01', end_date='2022-06-30', fq=1)

def get_EMA(df,length):
    k = 2/(length+1)
    df2 = [0]*len(df)     # 数组形式
    for i in range(len(df)):
        if i==0:
            df2[i] = df[i]
        if i>0:
            df2[i] = k * df[i] + (1-k) * df2[i-1]
    return np.asarray(df2)

