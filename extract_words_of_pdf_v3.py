import pdfplumber
import pandas as pd
from collections import Counter
from googletrans import Translator
from gtts import gTTS
import os
import time
import random
import json
import glob
import sys

def find_pdf_in_directory():
    """Busca archivos PDF en el directorio actual y permite seleccionar uno"""
    pdf_files = glob.glob("*.pdf") + glob.glob("*.PDF")  # Busca ambas extensiones
    
    if not pdf_files:
        print("\n⚠️ No se encontraron archivos PDF en esta carpeta.")
        print("Por favor coloca tu libro PDF en la misma carpeta que este script.")
        return None
    
    print("\n📄 Archivos PDF encontrados:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"{i}. {pdf}")
    
    try:
        selection = input("\n👉 Introduce el número del archivo a procesar (o Enter para el primero): ").strip()
        selection = int(selection) - 1 if selection else 0
        selected_pdf = pdf_files[selection]
        print(f"\n✅ Seleccionado: {selected_pdf}")
        return selected_pdf
    except (ValueError, IndexError) as e:
        print(f"\n❌ Error: Selección inválida ({str(e)}). Usando el primer archivo por defecto.")
        return pdf_files[0]

def extract_unique_words(pdf_path):
    """Extrae palabras únicas del PDF con filtros avanzados"""
    print(f"\n🔍 Extrayendo palabras de: {os.path.basename(pdf_path)}...")
    all_text = ""
    start_time = time.time()
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                all_text += text.lower() + " "
            
            # Mostrar progreso cada 10% del libro
            if i % max(1, total_pages//10) == 0 or i == total_pages:
                elapsed = time.time() - start_time
                pages_per_sec = i / max(1, elapsed)
                print(f"\r📖 Progreso: {i}/{total_pages} páginas ({i/total_pages:.0%}) | Velocidad: {pages_per_sec:.1f} pág/s", end="", flush=True)
    
    # Procesamiento de texto avanzado
    print("\n\n🧹 Limpiando y filtrando palabras...")
    words = ''.join([c if c.isalpha() or c in ["'", "-"] or c.isspace() else ' ' for c in all_text]).split()
    
    # Lista extendida de stopwords en inglés
    stop_words = {
        "the", "and", "to", "of", "a", "in", "that", "it", "with", "for", "is", "on", "as", "at", "be", "by", 
        "an", "this", "from", "or", "but", "not", "are", "were", "was", "have", "has", "had", "been", "will", 
        "would", "can", "could", "which", "what", "when", "where", "who", "whom", "how", "why", "if", "then", 
        "else", "there", "here", "their", "his", "her", "your", "my", "its", "our", "them", "him", "she", "he", 
        "we", "us", "i", "you", "me", "they", "them", "these", "those", "any", "some", "such", "no", "nor", 
        "so", "than", "too", "very", "just", "also", "now", "should", "might", "must", "about", "into", "over", 
        "under", "again", "further", "then", "once", "more", "most", "many", "few", "other", "same", "own", "each"
    }
    
    filtered_words = [
        word for word in words 
        if len(word) > 2 
        and word not in stop_words 
        and any(char.isalpha() for char in word)  # Debe contener al menos una letra
    ]
    
    # Contar frecuencia y ordenar
    word_counter = Counter(filtered_words)
    unique_words = sorted(word_counter.keys(), key=lambda w: word_counter[w], reverse=True)
    
    return unique_words, word_counter

def translate_with_progress(words, word_counter, source_lang='en', target_lang='es'):
    """Traduce palabras con persistencia y manejo de errores mejorado"""
    progress_file = "translation_progress.json"
    translations = {}
    
    # Cargar progreso existente
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        print(f"\n♻️ Cargado progreso existente ({len(progress)} traducciones)")
    else:
        progress = {}
    
    translator = Translator()
    total_words = len(words)
    start_time = time.time()
    
    print("\n🌍 Iniciando traducción (paciencia, puede tomar tiempo)...")
    print("--------------------------------------------------")
    
    for i, word in enumerate(words, 1):
        # Saltar palabras ya traducidas
        if word in progress:
            translations[word] = progress[word]
            continue
            
        try:
            # Traducción con manejo de errores
            translation = translator.translate(word, src=source_lang, dest=target_lang).text
            translations[word] = translation
            progress[word] = translation
            
            # Mostrar progreso detallado
            elapsed = time.time() - start_time
            words_per_min = (i / max(1, elapsed)) * 60
            print(f"\r🔄 {i}/{total_words} ({i/total_words:.0%}) | {words_per_min:.1f} palabras/min | {word} → {translation}", end="")
            
            # Guardar progreso cada 10 palabras
            if i % 10 == 0 or i == total_words:
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False)
            
            # Pausa aleatoria segura
            time.sleep(random.uniform(0.8, 2.5))
            
        except Exception as e:
            print(f"\n⚠️ Error traduciendo '{word}': {str(e)}")
            translations[word] = "ERROR"
            progress[word] = "ERROR"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False)
            time.sleep(5)  # Pausa más larga tras error
    
    print("\n✅ Traducción completada!")
    return translations

def generate_audio(words, translations, source_lang='en'):
    """Genera archivos de audio con gestión de errores mejorada"""
    audio_dir = "vocabulario_audios"
    os.makedirs(audio_dir, exist_ok=True)
    progress_file = os.path.join(audio_dir, "audio_progress.json")
    
    # Cargar progreso existente
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        print(f"\n♻️ Cargado progreso de audio ({len(progress)} archivos existentes)")
    else:
        progress = {}
    
    audio_files = {}
    total_words = len(words)
    start_time = time.time()
    
    print("\n🔊 Generando archivos de audio...")
    print("--------------------------------------------------")
    
    for i, word in enumerate(words, 1):
        safe_word = "".join(c for c in word if c.isalnum()).lower()
        audio_filename = f"{safe_word}.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        # Saltar si ya existe
        if word in progress and os.path.exists(audio_path):
            audio_files[word] = audio_filename
            continue
            
        try:
            # Generar audio con gTTS
            tts = gTTS(text=word, lang=source_lang, slow=False)
            tts.save(audio_path)
            audio_files[word] = audio_filename
            progress[word] = audio_filename
            
            # Mostrar progreso
            elapsed = time.time() - start_time
            audios_per_min = (i / max(1, elapsed)) * 60
            print(f"\r🎧 {i}/{total_words} ({i/total_words:.0%}) | {audios_per_min:.1f} audios/min | {word}", end="")
            
            # Guardar progreso cada 20 audios
            if i % 20 == 0 or i == total_words:
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False)
            
            # Pequeña pausa
            time.sleep(0.3)

            
        except Exception as e:
            print(f"\n⚠️ Error generando audio para '{word}': {str(e)}")
            audio_files[word] = "ERROR"
            progress[word] = "ERROR"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False)
            time.sleep(2)
    
    print("\n✅ Generación de audio completada!")
    return audio_files

def main():
    print("""
    ==================================================
    📚 EXTRACTOR DE VOCABULARIO PARA ANKI - VERSIÓN 3.0
    ==================================================
    Características:
    - Extrae palabras únicas de PDFs
    - Traduce automáticamente (inglés → español)
    - Genera pronunciaciones en audio
    - Persistencia de progreso (puedes pausar/reanudar)
    - Salida lista para Anki
    """)
    
    # Paso 1: Seleccionar PDF automáticamente
    pdf_path = find_pdf_in_directory()
    if not pdf_path:
        pdf_path = input("\n🛑 Introduce manualmente la ruta al archivo PDF: ").strip()
    
    if not os.path.exists(pdf_path):
        print("\n❌ Error: El archivo PDF no existe. Verifica la ruta.")
        return
    
    # Configuración de salida
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_file = f"{base_name}_vocabulario"
    
    # Paso 2: Extraer palabras
    unique_words, word_counter = extract_unique_words(pdf_path)
    
    print("\n" + "="*60)
    print(f"📊 EXTRACCIÓN COMPLETADA: {len(unique_words)} palabras únicas encontradas")
    if unique_words:
        most_common = max(word_counter, key=word_counter.get)
        print(f"🔠 Palabra más frecuente: '{most_common}' ({word_counter[most_common]} apariciones)")
    
    # Mostrar muestra de palabras
    sample_size = min(10, len(unique_words))
    sample = random.sample(unique_words, sample_size) if len(unique_words) > 10 else unique_words
    print(f"\n🔍 Muestra aleatoria: {', '.join(sample)}{'...' if len(unique_words)>10 else ''}")
    
    # Paso 3: Confirmación del usuario
    print("\n" + "="*60)
    user_input = input(f"\n¿Deseas traducir las {len(unique_words)} palabras y generar audios? (y/n): ").strip().lower()
    
    if user_input != 'y':
        # Guardar solo palabras sin traducir
        df = pd.DataFrame({
            'Palabra': unique_words,
            'Frecuencia': [word_counter[w] for w in unique_words]
        }, columns=['Palabra', 'Frecuencia'])
        
        output_path = f"{output_file}_sin_traducir.xlsx"
        df.to_excel(output_path, index=False)
        print(f"\n💾 Guardado en: {output_path}")
        return
    
    # Paso 4: Procesamiento completo
    print("\n" + "="*60)
    print("🚀 Iniciando proceso completo (traducción + audio)...")
    print("⚠️  Nota: Este proceso puede tomar tiempo. Puedes detenerlo y reanudar después.")
    print("="*60)
    
    # Traducción
    translations = translate_with_progress(
        unique_words, 
        word_counter,
        source_lang='en',
        target_lang='es'
    )
    
    # Generación de audio
    audio_files = generate_audio(
        unique_words,
        translations,
        source_lang='en'
    )
    
    # Crear DataFrame final
    df = pd.DataFrame({
        'Palabra': unique_words,
        'Traducción': [translations[w] for w in unique_words],
        'Frecuencia': [word_counter[w] for w in unique_words],
        'Audio': [audio_files[w] for w in unique_words]
    })
    
    # Exportar a Excel
    excel_path = f"{output_file}.xlsx"
    df.to_excel(excel_path, index=False)
    
    # Exportar para Anki (formato TSV)
    anki_path = f"{output_file}_anki.txt"
    with open(anki_path, 'w', encoding='utf-8') as f:
        for _, row in df.iterrows():
            audio_tag = f"[sound:{row['Audio']}]" if row['Audio'] != "ERROR" else ""
            f.write(f"{audio_tag}\t{row['Palabra']}\t{row['Traducción']}\n")
    
    # Exportar CSV
    csv_path = f"{output_file}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # Resumen final
    success_translations = sum(1 for t in translations.values() if t != "ERROR")
    success_audios = sum(1 for a in audio_files.values() if a != "ERROR")
    
    print("\n" + "="*60)
    print("🎉 ¡PROCESO COMPLETADO!")
    print(f"📊 Estadísticas:")
    print(f"- Palabras totales: {len(unique_words)}")
    print(f"- Traducciones exitosas: {success_translations} ({success_translations/len(unique_words):.0%})")
    print(f"- Audios generados: {success_audios} ({success_audios/len(unique_words):.0%})")
    
    print("\n📂 Archivos generados:")
    print(f"1. Excel completo: {excel_path}")
    print(f"2. CSV: {csv_path}")
    print(f"3. Importación Anki: {anki_path}")
    print(f"4. Carpeta de audios: vocabulario_audios/")
    
    print("\n💡 Para importar en Anki:")
    print("1. Copia la carpeta 'vocabulario_audios' a:")
    print("   Windows: C:0\\Users\\[tu_usuario]\\AppData\\Roaming\\Anki2\\[tu_perfil]\\collection.media\\")
    print("   Mac: ~/Documents/Anki2/[tu_usuario]/collection.media/")
    print("2. En Anki: Archivo → Importar → Selecciona el archivo _anki.txt")
    print("3. Configura como 'Basic (and reversed card)'")
    print("Si tienes problemas al importar revisa el README de este proyecto en Github")

if __name__ == "__main__":
    main()