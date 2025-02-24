# -*- coding: utf-8 -*-



"""
一、工具包导入
"""
from atrader import *
import numpy as np
import talib as ta

"""
二、初始化
"""
def init(context):
    # 注册数据
    reg_kdata('day', 1)                         # 注册日频行情数据
    # 回测细节设置
    set_backtest(initial_cash=1e8)              # 初始化设置账户总资金
    # 全局变量定义/参数定义
    context.Tlen = len(context.target_list)     # 标的数量
    context.win = 21                            # 计算所需总数据长度
    
    context.midline = 20       #  中轨均线值
    context.k = 1.2           # k的参数
    
"""
三、策略运行逻辑函数
"""

# 数据（行情/仓位）——计算逻辑(指标)——下单交易（无持仓/持多单/持空单）

def on_data(context):
    # 获取注册数据
    ##  全部行情数据获取
    data = get_reg_kdata(reg_idx=context.reg_kdata[0], length=context.win, fill_up=True, df=True)      # 所有标的的K线行情数据
    if data['close'].isna().any():                                    # 行情数据若存在nan值，则跳过
        return
    ## 从全部行情数据中获取想要的数据
    close = data.close.values.reshape(-1, context.win).astype(float)   # 获取收盘价，并转为ndarray类型的二维数组
     # 仓位数据查询,是一个数组
    positions_long = context.account().positions['volume_long']            # 获取仓位数据：positions=0，表示无持仓
    positions_short = context.account().positions['volume_short'] 
    
    
    # 循环交易每一个标的
    for i in range(context.Tlen):
        
        # 逻辑计算，计算均线
        # 一、自我编写法
        #MidLine = close[i,-context.midline:].mean()  # 中轨
        #std = close[i,-context.midline:].std()       # 标准差
        #UpLine = MidLine + context.k * std           # 上轨
        #DownLine = MidLine - context.k * std         # 下轨
        
        # 二、talib法
        upperband, middleband, lowerband = ta.BBANDS(close[i,:], 
                                                     timeperiod=context.midline, 
                                                     nbdevup=context.k, nbdevdn=context.k, matype=0)
        UpLine = upperband[-1]
        MidLine = middleband[-1]
        DownLine = lowerband[-1]
        
        # 下单交易
        # 无持仓
        if positions_long[i] == 0 & positions_short[i] ==0:  # 无持仓
            if close[i,-1] > UpLine:
                # 多单进场
                order_target_value(account_idx=0, target_idx=i, 
                                   target_value=1e8/context.Tlen, side=1,order_type=2, price=0) # 多头下单
            elif close[i,-1] < DownLine:
                # 空单进场
                order_target_value(account_idx=0, target_idx=i, 
                                   target_value=1e8/context.Tlen, side=2,order_type=2, price=0) # 空头下单
                
        # 持有多单
        elif positions_long[i] > 0:   # 持多仓
            if close[i,-1] < MidLine:
                # 多单出场
                order_target_value(account_idx=0, target_idx=i, target_value=0, side=1,order_type=2, price=0)
           
        # 持有空单
        elif positions_short[i] >0:
            if close[i,-1] > MidLine:
                # 空单进场
                order_target_value(account_idx=0, target_idx=i, target_value=0, side=2,order_type=2, price=0)


"""
四、策略执行脚本
"""
if __name__ == '__main__':
    # 策略回测函数
    target_list = ['SHFE.RB0000', 'SHFE.HC0000', 'SHFE.CU0000','SHFE.ZN0000']  # 设置回测标的
    run_backtest(strategy_name='Boll', file_path=r'E:\Users\OneDrive\桌面\策略构建过程和实现\Boll.py', target_list=target_list,
                 frequency='day', fre_num=1, begin_date='2018-01-01', end_date='2021-03-01', fq=1)


            
    
    