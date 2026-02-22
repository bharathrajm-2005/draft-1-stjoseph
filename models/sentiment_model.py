from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class SentimentModel:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text):
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        
        if compound >= 0.05:
            sentiment = "Positive"
        elif compound <= -0.05:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        return sentiment, compound
