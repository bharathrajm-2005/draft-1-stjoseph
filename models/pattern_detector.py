from collections import Counter
import re

class PatternDetector:
    def __init__(self):
        pass

    def detect_patterns(self, feedback_list):
        """ Detects common words across multiple feedback entries """
        if not feedback_list:
            return []
        
        all_text = " ".join(feedback_list).lower()
        words = re.findall(r'\w+', all_text)
        
        # Filter short words
        stop_words = ['the', 'and', 'was', 'for', 'with', 'this', 'that']
        words = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return Counter(words).most_common(5)
