
"""
一、工具包导入
"""
from atrader import *
import numpy as np
import pandas as pd

"""
二、初始化
"""
def init(context):
    # 注册数据
    reg_kdata('day', 1)                           # 注册日频行情数据
    # 回测细节设置
    set_backtest(initial_cash=1e8,                # 初始资金
                 margin_rate=1.0,                 # 保证金倍数
                 future_cost_fee=1.0,             # 期货手续费
                 slide_price=0,                   # 滑点设置
                 price_loc=1,                     # 市价单成交位置
                 deal_type=0)                     # 市价单成交类型
                 
    # 全局变量定义/参数定义
    context.initial = 1e8                          # 初始化设置账户总资金
    context.win = 22                               # 计算所需总数据长度，需比进场数据长度大2
    context.system_in = 20                      # 系统的进场数据长度
    context.system_out = 10                     # 系统的出场数据长度
    context.ATR_N = 20                             # ATR的数据长度
    context.add = 0.005                             # 加仓参数
    context.stop_loss = 2                          # 止损参数
    context.Tlen = len(context.target_list)        # 标的数量
    context.record_entryP = np.array(np.zeros(context.Tlen))     # 记录入场点位
    context.future_info = get_future_info(context.target_list)   # 获取期货标的基本信息

"""
三、策略运行逻辑函数
"""
def on_data(context):
    # 获取注册数据
    data = get_reg_kdata(reg_idx=context.reg_kdata[0], length=context.win, fill_up=True, df=True)
    if data['close'].isna().any():    # 行情数据若存在nan值，则跳过
        return
    # 仓位数据查询
    long_positions = context.account().positions['volume_long']    # 获取多头仓位数据
    short_positions = context.account().positions['volume_short']  # 获取空头仓位数据
    
    # 数据计算
    close = data.close.values.reshape(-1, context.win).astype(float)   # 获取收盘价，并转为ndarray类型的二维数组
    high = data.high.values.reshape(-1, context.win).astype(float)     # 获取最高价，并转为ndarray类型的二维数组
    low = data.low.values.reshape(-1, context.win).astype(float)       # 获取最低价，并转为ndarray类型的二维数组

    # 逻辑计算
    for i in range(context.Tlen):

        # 计算系统进出场唐奇安通道
        system_in_up = max(high[i,-context.system_in-1:-1])                   # 系统的进场的上轨
        system_in_down = min(low[i, -context.system_in-1:-1])                 # 系统的进场的下轨
        system_out_up = max(high[i,-context.system_out-1:-1])                 # 系统的出场的上轨
        system_out_down = min(low[i, -context.system_out-1:-1])               # 系统的出场的下轨

        # ATR计算
        HL = (high[i,-context.ATR_N-1:-1] - low[i,-context.ATR_N-1:-1])          # 当前交易日的最高价与最低价间的波幅
        HC = abs(high[i,-context.ATR_N-1:-1] - close[i,-context.ATR_N-2:-2])     # 前一交易日收盘价与当个交易日最高价间的波幅
        CL = abs(low[i,-context.ATR_N-1:-1] - close[i,-context.ATR_N-2:-2])      # 前一交易日收盘价与当个交易日最低价间的波幅
        TR = np.max([HL,HC,CL],axis = 0)                                         # n日的真实波幅
        ATR = TR.mean()                                                          # n日的真实波幅的均值

        # 每次要买入的仓位
        min_move = context.future_info['min_move'][i]                           # 标的最小变动单位
        Unit = context.initial * 0.01 / (ATR * min_move) / context.Tlen           # 标的每次买入仓位


        # 无持仓—进场
        if (long_positions[i] == 0) & (short_positions[i] == 0):   # 无持仓
            if close[i,-1] > system_in_up:                                                # 进多单
                order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=1, order_type=2)
                context.record_entryP[i] = close[i,-1]             # 记录进场价格

            elif close[i,-1] < system_in_down:                                            # 进空单
                order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=2, order_type=2)
                context.record_entryP[i] = close[i, -1]            # 记录进场价格

        # 持多仓—加仓/出场
        elif (long_positions[i] > 0):     # 持有多单
            if close[i, -1] > context.record_entryP[i] + context.add * ATR:                # 多单加仓
                order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=1, order_type=2)
                context.record_entryP[i] = close[i, -1]            # 记录进场价格

            elif close[i, -1] < system_out_down:                                           # 多单离市
                order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=1, order_type=2)
                context.record_entryP[i] = 0

            elif close[i, -1] < context.record_entryP[i] - context.stop_loss * ATR:        # 多单止损
                order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=1, order_type=2)
                context.record_entryP[i] = 0

        # 持空仓—加仓/出场
        elif (short_positions[i] > 0):     # 持有空单
            if close[i,-1] <  context.record_entryP[i] - context.add * ATR :               # 空单加仓
                order_target_volume(account_idx=0,target_idx=i,target_volume=int(Unit),side=2, order_type=2)
                context.record_entryP[i] = close[i, -1]            # 记录进场价格

            elif close[i, -1] > system_out_up:                                             # 空单离市
                order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=2, order_type=2)
                context.record_entryP[i] = 0

            elif close[i,-1] > context.record_entryP[i] + context.stop_loss * ATR:         # 空单止损
                order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=2, order_type=2)
                context.record_entryP[i] = 0

"""
四、策略执行脚本
"""
if __name__ == '__main__':
    target_list = ['SHFE.zn0000', 'SHFE.rb0000']                    # 设置回测标的
    # 策略回测函数
    run_backtest(strategy_name='Turtle', file_path=r'E:\Users\OneDrive\桌面\日间策略\Turtle.py', target_list=target_list,
                 frequency='week', fre_num=5, begin_date='2016-01-01', end_date='2017-01-01', fq=1)
        # 下单交易      
        # if (nowtime < 1455) | (nowtime > 1500):
            # if (long_positions[i] == 0) & (short_positions[i] == 0):  # 无持仓
            #     if (close[i,-1] > Buyline[-1]) & (close[i,-2] < Buyline[-2]):
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=1, order_type=2)#进多单
            #         context.record_entryP[i] = close[i,-1]             # 记录进场价格
                    
            #     elif (close[i,-1] < Sellline) & (close[i,-2] > Sellline[-2]):
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=2, order_type=2)#进空单
            #         context.record_entryP[i] = close[i, -1]            # 记录进场价格
                    
            # elif long_positions[i] > 0:                 # 持有多头
            #     if (close[i,-1] > Buyline[-1]) & (close[i,-2] < Buyline[-2]):                    # 多头加仓
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=int(Unit), side=1, order_type=2)
            #         context.record_entryP[i] = close[i, -1]            # 记录进场价格
            
            #     elif (close[i,-1] < Midline[-1]) & (close[i,-2] > Midline[-2]):                          # 多头离市
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=1, order_type=2)
            #         context.record_entryP[i] = 0
            
            #     elif close[i,-1] < context.record_entryP[i] - 2 * ATR:               # 多头止损
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=1, order_type=2)
            #         context.record_entryP[i] = 0
           
            # elif short_positions[i] > 0:                # 持有空头
            #     if (close[i,-1] < Sellline[-1]) & (close[i,-2] > Sellline[-2]):                    # 空头加仓
            #         order_target_volume(account_idx=0,target_idx=i,target_volume=int(Unit),side=2, order_type=2)
            #         context.record_entryP[i] = close[i, -1]   
            
            #     elif (close[i,-1] < Midline[-1]) & (close[i,-2] > Midline[-2]):                          # 空头离市
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=2, order_type=2)
            #         context.record_entryP[i] = 0
            
            #     elif close[i,-1] > context.record_entryP[i] + 2 * ATR:             # 空头止损
            #         order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=2, order_type=2)
            #         context.record_entryP[i] = 0

