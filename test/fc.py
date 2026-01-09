import regex


def clean_text(text):
    return ''.join(c for c in text if regex.match(r'[\p{Han}\p{Latin}0-9\s.,!?？。，！；（）：‘’【】、;:\'"\-()（）\[\]{}…—·~`@#&*+=<>%$^|\\/]', c))

if __name__ == "__main__":
    res = clean_text(input())
    print(res)