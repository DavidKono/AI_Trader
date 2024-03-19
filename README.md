# AI_Trader
A program that takes current news events and uses the openAI API to predict market movements, and create orders in the Alpaca trading API

Note alpaca trading api marks you as a pattern day trader for making more than 3 trades a day, ideally take more certain trades, ie chatgpt certainty of 80+, and trade more volume on these trades eg 20% of cash balance. Margin trades would work for this as well.
This program is set up to take 3x more profit than loss with its stops, however it looks for an unrealistic 6% growth in a short timeframe, and 6% decline for shorts. Apart from cases such as an early buy in a tech stock, it is recommended to manually close trades at a certain point, or set the default growth to 3% for the limit price and vice versa.
