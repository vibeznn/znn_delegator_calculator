import requests
import math
import sys

import pandas as pd
import numpy as np

pd.set_option('display.width', 1500)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.max_columns', 100)


DAILY_ZNN_REWARDS_PER_MONTH = [14_400, 8_640, 7_200, 10_080, 7_200, 5_760, 10_080, 5_760, 4_320, 10_080, 4_320, 4_320]
DAYS_IN_MONTH = 30
PILLAR_REWARDS = 0.5
DELEGATION_REWARDS = 0.24
MOMENTUMS_PER_DAY = 8640
MOMENTUMS_PER_ALLOCATION = 30
ALPHANET_START = '2021-11-21 12:00:00'


def __days_since_alphanet():
    """
    Calculates days since Alphanet BigBang.

    Returns:
        int: days since BigBang
    """
    return (pd.to_datetime('today') - pd.to_datetime(ALPHANET_START)).days
    
    
def __get_current_daily_znn_rewards():
    """
    This function calculates the amount of full months since Alphanet Big Bang. 
    Using the amount of months it returns the daily rewards.

    Returns:
        int: daily znn rewards
    """
    months_since_big_bang = math.floor(__days_since_alphanet()/DAYS_IN_MONTH)
    return DAILY_ZNN_REWARDS_PER_MONTH[months_since_big_bang]
    

def calculate_expected_momentums(amount_of_pillars, days=2):
    """
    This function calculates the expected number of momentums produced over a day.
    It does so by simulating the pseudo-random allocation of momentums as 
    presented in https://medium.com/@zenon.network/znn-x-qsr-alphanet-specifications-83d27c005c09.
    It then gives the average of expected momentums for top 30 pillars and other pillars for one day.
    
    Top 30 pillars are represented by the first 30 indexes in df_pillars.
    Args:
        amount_of_pillars (int): Amount of pillars producing Momentums in NoM
        days (int): Days you want to use in the simulation, using more days gives less variation in output.
                    Output is still calculated for one day. 

    Returns:
        tuple: tuple containing (expected momentums from a top 30 pillar,
                                    expected momentums from a non top-30 pillar)
    """
    if amount_of_pillars < 30:
        raise ValueError('Amount_of_pillars must be greater or equal than 30') 
    
    amount_of_momentum_allocations = int(MOMENTUMS_PER_DAY * days / MOMENTUMS_PER_ALLOCATION)
    df_pillars = pd.DataFrame({'pillar': [i for i in range(1, amount_of_pillars + 1)],
                                       'momentums': 0})
    
    # Below loop simulates the pseudorandom allocation of pillars which will produce momentums
    for i in range(amount_of_momentum_allocations):
        # sample 15 pillars from top 30 pillars
        first_sample = df_pillars\
            .iloc[0:30]\
            .sample(n=15)['pillar'].tolist()
        
        # sample 15 pillars from pillars not in previous lot
        second_sample = df_pillars\
            .loc[~df_pillars['pillar'].isin(first_sample)]\
            .sample(n=15)['pillar'].tolist()

        lucky_pillars = first_sample + second_sample
        lucky_indexes = df_pillars['pillar'].isin(lucky_pillars)
        df_pillars.loc[lucky_indexes, 'momentums'] = df_pillars.loc[lucky_indexes, 'momentums'] + 1
    
    top_thirty_pillar_expected_momentums = int(df_pillars.loc[0:30, 'momentums'].mean() / days)
    other_pillars_expected_momentums = int(df_pillars.loc[30:, 'momentums'].mean() / days)
    
    return top_thirty_pillar_expected_momentums, other_pillars_expected_momentums


def get_rewards_per_pillar(my_balance=100, current_pillar=''):
    """
    This function gets all current pillars in NoM. For all pillars both momentum rewards
    and delegation rewards are calculated for a user delegating to a pillar. It returns a
    Pandas DataFrame containing columns for rewards. Set my_balance to 100 to see daily APR.

    Args:
        my_balance (int, optional): Your delegation balance in a single address. Defaults to 100.
        current_pillar (str, optional): If you're already delegating to a pillar, fill in the name here
                        this prevents the weight from getting diluted twice by own balance. Defaults to ''.

    Returns:
        pd.DataFrame: pandas DataFrame containing pillar rewards.
    """
    
    full_node_url = "http://178.62.223.132:35997"

    # Example echo method
    payload = {
        "method": "embedded.pillar.getAll",
        "params": [0, 200],
        "jsonrpc": "2.0",
        "id": 3}
    
    daily_rewards = __get_current_daily_znn_rewards()
    
    response = requests.post(full_node_url, json=payload).json()
    df_response = pd.DataFrame(response['result']['list'])
    print(f'Amount of pillars: {len(df_response)}')
    del response
    
    df_rewards = df_response.loc[:,['name', 
                                    'giveMomentumRewardPercentage', 
                                    'giveDelegateRewardPercentage', 
                                    'currentStats', 
                                    'weight']]
    
    df_rewards = pd.concat([df_rewards.drop(['currentStats'], axis=1), 
                            df_rewards['currentStats'].apply(pd.Series)], axis=1)
    
    df_rewards['producedRate'] = df_rewards['producedMomentums'] / df_rewards['expectedMomentums']

    df_rewards['weight'] = round(df_response['weight']/100000000)
    df_rewards['weight'] = df_rewards['weight'].astype(int)
    
    # Add my balance to all pillars' weight except the pillar im currently delegating to.
    df_rewards['weight'] = np.where(df_rewards['name'] == current_pillar,
                                    df_rewards['weight'], 
                                    df_rewards['weight'] + my_balance)

    df_rewards.sort_values('weight', ascending=False, inplace=True)
    df_rewards['pillarRank'] = df_rewards.index + 1
    
    momentum_rewards = daily_rewards * PILLAR_REWARDS / MOMENTUMS_PER_DAY 
    
    top_thirty_pillar_expected_momentums, other_pillars_expected_momentums = \
        calculate_expected_momentums(len(df_rewards.loc[df_rewards['producedRate'] > 0]))
    
    df_rewards['epochExpectedMomentums'] = np.where(df_rewards['pillarRank'] <= 30, 
                                                top_thirty_pillar_expected_momentums, 
                                                other_pillars_expected_momentums)
    
    df_rewards['epochExpectedMomentumRewards'] = \
        df_rewards['epochExpectedMomentums'] * df_rewards['producedRate'] * momentum_rewards
    
    df_rewards['momentumRewardsForMe'] = df_rewards['epochExpectedMomentumRewards'] * \
                                            (df_rewards['giveMomentumRewardPercentage']/100) * \
                                            (my_balance/df_rewards['weight'])
    
    print(f'Total delegated ZNN: {df_rewards.weight.sum()}')     
                                       
    df_rewards['delegationRewardsForMe'] = daily_rewards * DELEGATION_REWARDS * \
                                            my_balance/df_rewards.weight.sum() * \
                                            (df_rewards['giveDelegateRewardPercentage']/100)
    
    df_rewards['epochRewardsForMe'] = df_rewards['momentumRewardsForMe'] + df_rewards['delegationRewardsForMe']
    
    df_rewards.rename({'giveMomentumRewardPercentage': 'MomentumReward%',
                       'giveDelegateRewardPercentage': 'DelegateReward%'}, axis=1, inplace=True)
    
    df_rewards.to_csv('pillars_with_delegation_rewards.csv', index=False)
    
    return df_rewards.sort_values(['epochRewardsForMe'], ascending=False).reset_index(drop=True)


if __name__ == "__main__":   
    df = get_rewards_per_pillar(my_balance=100, current_pillar='')
    print(df)