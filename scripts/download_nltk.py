import nltk

def download_nltk_resources():
    resources = [
        'punkt',
        'punkt_tab',
        'stopwords',
        'wordnet',
        'omw-1.4',
        'averaged_perceptron_tagger'
    ]
    for resource in resources:
        try:
            print(f"Downloading {resource}...")
            nltk.download(resource)
        except Exception as e:
            print(f"Failed to download {resource}: {e}")

if __name__ == "__main__":
    download_nltk_resources()
