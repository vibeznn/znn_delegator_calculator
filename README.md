# znn_delegator_calculator
Script to calculate *estimated* delegator epoch returns for all Pillars, so you can delegate to the best one.  

You can find me on TG: @vibeznn  
If you'd like to donate for future scripts and data science projects on/around NoM please send to:  
z1qpn04kmqdn9qyx45znwr2stnerqm8rg0y2vdm8 (NetworkofMomentum)  
Thanks!


## Usage
You can run this script from an IDE or from commandline with "python3 delegator_calculator.py".

When you run this script it defaults to 100 znn delegation size, so the epochRewardsForMe columns is equal to *daily APR*.  
You can edit the script to include the current pillar you're delegated to on line 176  with current_pillar = 'PILLAR NAME'.   
This way your own delegated weight isn't added to that pillar, as this would dilute the APR while you're already diluting it.  
For all other pillars it adds your balance to the weight so that estimated returns are as accurate as possible.  
You can also leave it empty, then your balance is added to all Pillars' weight. 


## Output
This script prints the output in your terminal or IDE and also saves a CSV of the resulting table.  

Online tool + dashboard might be coming soon.  