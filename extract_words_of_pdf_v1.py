import pdfplumber
import string
import pandas as pd
from collections import Counter

def extract_unique_words(pdf_path, output_file):
    # Configuración
    all_text = ""
    stop_words = {"the", "and", "to", "of", "a", "in", "that", "it", "with", "for"}  # Personalizable
    
    # Extraer texto del PDF
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text.lower() + " "

    # Limpiar y tokenizar
    translator = str.maketrans('', '', string.punctuation + '“”‘’')
    clean_text = all_text.translate(translator)
    words = clean_text.split()

    # Filtrar y contar
    unique_words = set()
    word_counter = Counter()
    for word in words:
        if (len(word) > 2 and 
            word not in stop_words and 
            not word.isdigit() and 
            word.isalpha()):
            unique_words.add(word)
            word_counter[word] += 1

    # Guardar resultados
    df = pd.DataFrame({
        'word': list(unique_words),
        'frequency': [word_counter[w] for w in unique_words]
    })
    
    # Ordenar por frecuencia (opcional)
    df = df.sort_values(by='frequency', ascending=False)
    
    # Guardar en múltiples formatos
    df.to_excel(output_file + '.xlsx', index=False)
    df.to_csv(output_file + '.csv', index=False)
    
    with open(output_file + '.txt', 'w') as f:
        f.write('\n'.join(unique_words))

# Uso del script
if __name__ == "__main__":
    extract_unique_words(
        pdf_path="ruta/a/tu/libro.pdf",
        output_file="vocabulario_ingles"
    )