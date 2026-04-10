# dl_models/utils/colors.py

import numpy as np

def get_dominant_color(image):
    # image = PIL → numpy
    img = np.array(image)
    
    # moyenne RGB
    mean_color = img.mean(axis=(0, 1))  # [R, G, B]
    
    r, g, b = mean_color

    # règles simples
    if r > 150 and g > 150 and b > 150:
        return 1  # blanc
    elif r < 80 and g < 80 and b < 80:
        return 0  # noir
    elif r > g and r > b:
        return 3  # roux
    elif g > r and g > b:
        return 4  # vert-ish (rare mais bon)
    elif b > r and b > g:
        return 2  # gris/bleu
    else:
        return 2  # gris par défaut
    

COLOR_MAP = {
    0: "noir",
    1: "blanc",
    2: "gris",
    3: "roux",
    4: "autre"
}