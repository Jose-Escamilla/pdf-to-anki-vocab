import pdfplumber
import pandas as pd
from collections import Counter
from googletrans import Translator
from gtts import gTTS
import os
import time
import random
import json
import sys

def extract_unique_words(pdf_path):
    """Extrae palabras únicas del PDF sin procesamiento adicional"""
    print(f"Extrayendo palabras de {pdf_path}...")
    all_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                all_text += text.lower() + " "
            # Mostrar progreso cada 10 páginas
            if i % 10 == 0 or i == total_pages - 1:
                print(f"\rProcesando página {i+1}/{total_pages}...", end="", flush=True)
    
    print("\nLimpiando y tokenizando texto...")
    # Reemplazar caracteres no alfabéticos por espacios, excepto apóstrofes y guiones internos
    cleaned_text = ''.join([c if c.isalpha() or c in ["'", "-"] or c.isspace() else ' ' for c in all_text])
    words = cleaned_text.split()
    
    # Filtrar palabras
    stop_words = {"the", "and", "to", "of", "a", "in", "that", "it", "with", "for", "is", "on", "as", "at", "be", "by", "an", "this", "from", "or", "but", "not", "are", "were", "was", "have", "has", "had", "been", "will", "would", "can", "could", "which", "what", "when", "where", "who", "whom", "how", "why", "if", "then", "else", "there", "here", "their", "his", "her", "your", "my", "its", "our", "them", "him", "she", "he", "we", "us", "i", "you", "me", "they", "them", "these", "those", "any", "some", "such", "no", "nor", "so", "than", "too", "very", "just", "also", "now"}
    filtered_words = [
        word for word in words 
        if len(word) > 2 
        and word not in stop_words 
        and any(char.isalpha() for char in word)  # Asegura que contenga al menos una letra
    ]
    
    # Obtener palabras únicas con frecuencia
    word_counter = Counter(filtered_words)
    unique_words = sorted(word_counter.keys(), key=lambda w: word_counter[w], reverse=True)
    
    return unique_words, word_counter

def translate_with_progress(words, word_counter, source_lang='en', target_lang='es', resume=True):
    """Traduce palabras con persistencia de progreso y manejo de errores"""
    # Archivo para guardar progreso
    progress_file = "translation_progress.json"
    
    if resume and os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        print(f"\nCargado progreso existente ({len(progress)} palabras traducidas)")
    else:
        progress = {}
    
    translator = Translator()
    translations = {}
    total_words = len(words)
    
    print("\nIniciando traducción...")
    print("--------------------------------------------------")
    
    for i, word in enumerate(words):
        # Saltar palabras ya procesadas
        if word in progress:
            translations[word] = progress[word]
            continue
            
        try:
            # Traducción con manejo de errores
            translation = translator.translate(word, src=source_lang, dest=target_lang).text
            translations[word] = translation
            progress[word] = translation
            
            # Guardar progreso cada 5 palabras
            if i % 5 == 0 or i == total_words - 1:
                with open(progress_file, 'w') as f:
                    json.dump(progress, f)
            
            # Mostrar progreso
            print(f"{i+1}/{total_words}: {word} → {translation}")
            
            # Pausa aleatoria
            time.sleep(random.uniform(0.8, 2.0))
            
        except Exception as e:
            print(f"Error traduciendo '{word}': {str(e)}")
            translations[word] = "ERROR"
            progress[word] = "ERROR"
            # Guardar inmediatamente en caso de error
            with open(progress_file, 'w') as f:
                json.dump(progress, f)
            # Pausa más larga en caso de error
            time.sleep(5)
    
    # Guardar progreso final
    with open(progress_file, 'w') as f:
        json.dump(progress, f)
    
    return translations

def generate_audio(words, translations, source_lang='en', resume=True):
    """Genera archivos de audio con persistencia de progreso"""
    audio_dir = "vocabulario_audios"
    os.makedirs(audio_dir, exist_ok=True)
    
    audio_progress_file = "audio_progress.json"
    processed_audios = {}
    
    if resume and os.path.exists(audio_progress_file):
        with open(audio_progress_file, 'r') as f:
            processed_audios = json.load(f)
        print(f"\nAudio: Progreso cargado ({len(processed_audios)} audios existentes)")
    
    audio_files = {}
    
    print("\nGenerando archivos de audio...")
    print("--------------------------------------------------")
    
    for i, word in enumerate(words):
        safe_word = "".join(c for c in word if c.isalnum()).lower()
        audio_filename = f"{safe_word}.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        # Saltar si ya existe y está registrado
        if word in processed_audios and os.path.exists(audio_path):
            audio_files[word] = audio_filename
            continue
            
        try:
            tts = gTTS(text=word, lang=source_lang, slow=False)
            tts.save(audio_path)
            audio_files[word] = audio_filename
            processed_audios[word] = audio_filename
            
            # Guardar progreso cada 10 palabras
            if i % 10 == 0 or i == len(words) - 1:
                with open(audio_progress_file, 'w') as f:
                    json.dump(processed_audios, f)
            
            print(f"{i+1}/{len(words)}: Audio generado para '{word}'")
            time.sleep(0.5)  # Pausa mínima para audio
            
        except Exception as e:
            print(f"Error generando audio para '{word}': {str(e)}")
            audio_files[word] = "ERROR"
            processed_audios[word] = "ERROR"
            # Guardar inmediatamente en caso de error
            with open(audio_progress_file, 'w') as f:
                json.dump(processed_audios, f)
    
    return audio_files

def main():
    # Configuración
    PDF_PATH = input("Introduce la ruta al archivo PDF: ").strip()
    if not os.path.exists(PDF_PATH):
        print(f"Error: El archivo {PDF_PATH} no existe.")
        return
    
    OUTPUT_FILE = os.path.splitext(os.path.basename(PDF_PATH))[0] + "_vocabulario"
    SOURCE_LANG = 'en'
    TARGET_LANG = 'es'
    
    # Paso 1: Extraer palabras
    unique_words, word_counter = extract_unique_words(PDF_PATH)
    
    print("\n" + "="*60)
    print(f"EXTRACCIÓN COMPLETADA: {len(unique_words)} palabras únicas encontradas")
    if unique_words:
        most_common_word = max(word_counter, key=word_counter.get)
        print(f"Palabra más frecuente: '{most_common_word}' ({word_counter[most_common_word]} apariciones)")
    
    # Mostrar muestra de palabras
    sample = unique_words[:min(10, len(unique_words))]
    print(f"\nMuestra de palabras: {', '.join(sample)}{'...' if len(unique_words)>10 else ''}")
    
    # Paso 2: Confirmación del usuario
    print("\n" + "="*60)
    user_input = input(f"¿Deseas traducir las {len(unique_words)} palabras y generar audios? (y/n): ").strip().lower()
    
    if user_input != 'y':
        # Guardar solo palabras sin traducir
        df = pd.DataFrame({
            'Palabra': unique_words,
            'Frecuencia': [word_counter[w] for w in unique_words]
        })
        output_path = f"{OUTPUT_FILE}_sin_traducir.xlsx"
        df.to_excel(output_path, index=False)
        print("\nGuardando solo palabras extraídas...")
        print(f"Archivo generado: {output_path}")
        return
    
    # Paso 3: Procesamiento completo
    print("\nIniciando proceso completo...")
    
    # Traducción
    translations = translate_with_progress(
        unique_words, 
        word_counter,
        source_lang=SOURCE_LANG,
        target_lang=TARGET_LANG
    )
    
    # Generación de audio
    audio_files = generate_audio(
        unique_words,
        translations,
        source_lang=SOURCE_LANG
    )
    
    # Crear DataFrame final
    df = pd.DataFrame({
        'Palabra': unique_words,
        'Traducción': [translations[w] for w in unique_words],
        'Frecuencia': [word_counter[w] for w in unique_words],
        'Audio': [audio_files[w] for w in unique_words]
    })
    
    # Exportar a Excel
    excel_path = f"{OUTPUT_FILE}.xlsx"
    df.to_excel(excel_path, index=False)
    
    # Exportar para Anki (formato TSV)
    anki_path = f"{OUTPUT_FILE}_anki.txt"
    with open(anki_path, 'w', encoding='utf-8') as f:
        for _, row in df.iterrows():
            audio_tag = f"[sound:{row['Audio']}]" if row['Audio'] != "ERROR" else ""
            # Formato: Frente <tab> Reverso (con audio en el frente)
            f.write(f"{audio_tag}\t{row['Palabra']}\t{row['Traducción']}\n")
    
    # Exportar un CSV por si acaso
    csv_path = f"{OUTPUT_FILE}.csv"
    df.to_csv(csv_path, index=False, sep=',', encoding='utf-8')
    
    print("\n" + "="*60)
    print("¡PROCESO COMPLETADO!")
    print(f"- Palabras procesadas: {len(unique_words)}")
    print(f"- Traducciones exitosas: {sum(1 for t in translations.values() if t != 'ERROR')}")
    print(f"- Audios generados: {sum(1 for a in audio_files.values() if a != 'ERROR')}")
    print(f"\nArchivos generados:")
    print(f"1. Excel completo: {excel_path}")
    print(f"2. CSV: {csv_path}")
    print(f"3. Importación Anki: {anki_path}")
    print(f"4. Carpeta de audios: vocabulario_audios/")
    print("\nRecuerda copiar la carpeta 'vocabulario_audios' a tu carpeta de medios de Anki (collection.media)")

if __name__ == "__main__":
    main()