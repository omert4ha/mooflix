import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import pandas as pd
from transformers import pipeline
import random

print("--- API Başlatılıyor: Modeller Yükleniyor ---")

# --- Adım 2.1: Hazır Duygu Analizi Modelini Yükleme ---
# Bu model, API'miz başlarken SADECE BİR KEZ yüklenir.
try:
    # 'model' parametresini yerel klasörümüzün yoluyla değiştiriyoruz
    emotion_classifier = pipeline("text-classification", 
                                 model="local_emotion_model",
                                 return_all_scores=True,
                                 framework="pt")
    print("Duygu analizi modeli (Yerel) başarıyla yüklendi.")
except Exception as e:
    # Gerçek hatayı görmek için 'e' değişkenini de yazdıralım
    print(f"HATA: Duygu analizi modeli yüklenemedi. Gerçek Hata: {e}")
    emotion_classifier = None
    #print(f"HATA: Duygu analizi modeli yüklenemedi. İnternet bağlantınızı kontrol edin. Hata: {e}")
    # Geliştirme aşamasındaysanız ve modeli indirmek uzun sürüyorsa,
    # bu kısmı geçici olarak yorum satırı yapıp, duygu_analizi fonksiyonunu 
    # manuel bir değer (örn: "sadness") döndürecek şekilde ayarlayabilirsiniz.
    #emotion_classifier = None # Geçici çözüm


# --- Adım 2.3: Faz 1'de Oluşturduğumuz Tavsiye Modelini Yükleme ---
try:
    # .pkl dosyalarını yükle
    movies_dict = pickle.load(open('movies_list.pkl', 'rb'))
    similarity = pickle.load(open('similarity.pkl', 'rb'))
    
    # .pkl'dan yüklediğimiz sözlüğü (dict) tekrar Pandas DataFrame'e çevirelim
    movies = pd.DataFrame(movies_dict)
    print("Tavsiye motoru modelleri (movies_list.pkl, similarity.pkl) başarıyla yüklendi.")
except FileNotFoundError:
    print("HATA: 'movies_list.pkl' veya 'similarity.pkl' dosyaları bulunamadı.")
    print("Lütfen Faz 1'deki script'i çalıştırdığınızdan emin olun.")
    exit()


# --- Adım 2.2: FastAPI Uygulamasını Başlatma ---
app = FastAPI()

# --- Tavsiye Motoru Yardımcı Fonksiyonu ---
def recommend(movie_title):
    """
    Verilen bir film adına göre en benzer 5 filmi önerir.
    """
    try:
        # Film adından, o filmin dataframe'deki index'ini bul
        movie_index = movies[movies['title'] == movie_title].index[0]
        
        # O index'teki filmin benzerlik skorlarını 'similarity' matrisinden çek
        # enumerate ile (index, skor) çiftleri oluşturup, skora göre tersten sırala
        distances = sorted(list(enumerate(similarity[movie_index])), reverse=True, key=lambda x: x[1])
        
        recommendations = []
        # Benzer 5 film al 
        for i in distances[1:6]:
            recommended_movie_title = movies.iloc[i[0]].title
            recommendations.append(recommended_movie_title)
            
        return recommendations
    except IndexError:
        # Verilen film adı veritabanında bulunamazsa
        print(f"HATA: '{movie_title}' filmi veritabanında bulunamadı.")
        return []
    except Exception as e:
        print(f"Tavsiye motorunda beklenmedik hata: {e}")
        return []

# --- Duygu Analizi Yardımcı Fonksiyonu ---
def analyze_emotion(text):
    """
    Verilen metnin en baskın duygusunu döndürür.
    """
    if emotion_classifier is None:
        print("UYARI: Duygu analizi modeli yüklenmedi, varsayılan 'sadness' kullanılıyor.")
        return "sadness" # Geçici çözüm için
        
    try:
        # Model metni analiz eder ve TÜM duygular için skor döndürür
        scores = emotion_classifier(text)
        
        # En yüksek skora sahip olan duyguyu bul
        # scores[0] bir liste döner: [{'label': 'sadness', 'score': 0.8}, {'label': 'joy', 'score': 0.1}, ...]
        if scores and scores[0]:
            dominant_emotion = sorted(scores[0], key=lambda x: x['score'], reverse=True)[0]['label']
            print(f"Metin: '{text}' -> Bulunan Duygu: '{dominant_emotion}'")
            return dominant_emotion
        else:
            return "neutral" # Bir şey bulamazsa
    except Exception as e:
        print(f"Duygu analizi sırasında hata: {e}")
        return "neutral" # Hata durumunda nötr dön


# --- Adım 2.4: Duyguları Filmlerle Eşleştirme (GÜNCELLENDİ: TREMO Etiketleri) ---
# Senin eğittiğin model artık bu etiketleri (Happy, Sadness vb.) döndürüyor.
# --- Adım 2.4: Duyguları Filmlerle Eşleştirme (GÜNCELLENMİŞ VERSİYON) ---
# --- DUYGU - FİLM HAVUZU (OMERT4HA PROFİLİNE ÖZEL) ---
emotion_movie_map = {
    # ÜZGÜN (Sadness) -> Klasik komedi yerine "Quality Comfort" veya "Dark Humor"
    "Sadness": [
        "The Big Lebowski",       # Coen Kardeşler klasiği
        "The Grand Budapest Hotel", # Wes Anderson estetiği
        "The Secret Life of Walter Mitty", # Görsel ve motive edici
        "Superbad",               # Kült komedi
        "Shaun of the Dead",      # Zeki İngiliz mizahı
        "Little Miss Sunshine",   # Kaliteli indie drama-komedi
        "Paddington 2"            # Sinefillerin gizli favorisi (şakasız)
    ],

    # MUTLU (Happy) -> Adrenalin, Zeka ve Görsellik (Nolan/Villeneuve tarzı)
    "Happy": [
        "Inception",              # Zirve noktası
        "Interstellar",           # Görsel şölen
        "Dune: Part Two",         # Modern epik
        "Mad Max: Fury Road",     # Saf aksiyon sineması
        "Spider-Man: Across the Spider-Verse", # Görsel devrim
        "Top Gun: Maverick",      # Kaliteli blockbuster
        "Baby Driver"             # Müzik ve kurgu uyumu
    ],

    # KIZGIN (Anger) -> Adalet, İntikam ve Sert Gerçekçilik (Fincher/Tarantino)
    "Anger": [
        "Fight Club",             # Öfke yönetiminin zirvesi
        "Se7en",                  # Karanlık ve atmosferik
        "John Wick",              # Saf intikam
        "Oldboy",                 # (2003) Kore sineması şaheseri
        "Django Unchained",       # Tarantino tarzı adalet
        "Taxi Driver",            # Karakter odaklı suç
        "Whiplash"                # Tutku ve öfke
    ],

    # KORKMUŞ (Fear) -> Ucuz korku değil; Psikolojik Gerilim (Kubrick/Aster)
    "Fear": [
        "The Shining",            # Kubrick klasiği
        "Hereditary",             # Modern korku başyapıtı
        "Get Out",                # Zeki senaryo
        "The Silence of the Lambs", # Suç/Gerilim
        "Alien",                  # Bilim kurgu/Korku atası
        "Prisoners",              # Denis Villeneuve gerilimi
        "Perfect Blue"            # Psikolojik anime gerilim
    ],

    # TİKSİNMİŞ (Disgust) -> Toplum eleştirisi ve Distopya
    "Disgust": [
        "Parasite",               # Sosyal sınıf eleştirisi
        "A Clockwork Orange",     # Kubrick distopyası
        "American Psycho",        # Kült hiciv
        "Nightcrawler",           # Medya eleştirisi
        "Joker",                  # Toplumsal çöküş
        "Requiem for a Dream"     # (Uyarı: Çok sert ama kaliteli)
    ],

    # ŞAŞIRMIŞ (Surprise) -> Plot Twist (Ters Köşe) Kralları
    "Surprise": [
        "The Prestige",           # Nolan'ın en iyi senaryolarından
        "Memento",                # Tersten akan kurgu
        "Shutter Island",         # Scorsese ve plot twist
        "Arrival",                # Dilbilim ve zaman
        "Gone Girl",              # Fincher gerilimi
        "The Usual Suspects"      # Finaliyle ünlü
    ],

    # BELİRSİZ (Ambigious) -> Kült ve Yoruma Açık Filmler
    "Ambigious": [
        "Donnie Darko",           # Kült bilim kurgu
        "Blade Runner 2049",      # Görsel şaheser
        "Eternal Sunshine of the Spotless Mind", # Zeki romantizm
        "Her",                    # Modern yalnızlık
        "Pulp Fiction"            # Tarantino klasiği
    ],

    # YEDEK -> Herkesin saygı duyduğu klasikler
    "neutral": ["The Godfather", "The Dark Knight", "Goodfellas"]
}
# Not: Listeden rastgele seçeceğiz ki hep aynı filmi görmesin.

# --- Flutter'dan Gelen İsteğin Modelini Tanımlama ---
class UserInput(BaseModel):
    text: str # Flutter bize "text" adında bir string yollayacak

# --- Flutter'dan Gelen Cevabın Modelini Tanımlama ---
class RecommendationResponse(BaseModel):
    emotion: str
    prototype_movie: str
    recommendations: list[str]

print("--- API Başlatılmaya Hazır ---")

# --- Adım 2.5: API Endpoint'i Oluşturma ---
@app.post("/recommend", response_model=RecommendationResponse)
def get_recommendations_for_emotion(user_input: UserInput):
    """
    Flutter'dan gelen metni alır, duyguyu analiz eder ve film önerilerini döndürür.
    """
    # 1. Metni al
    text = user_input.text
    
    # 2. Duyguyu analiz et
    emotion = analyze_emotion(text)
    
    # 3. Duyguya uygun prototip film listesini seç
    # Eğer modelin tanımadığı bir duygu gelirse (örn: "neutral"), varsayılan listeyi kullan
    prototype_list = emotion_movie_map.get(emotion, emotion_movie_map["neutral"])
    
    # 4. Listeden rastgele bir prototip film seç
    prototype_movie = random.choice(prototype_list)
    
    # 5. O prototip filme benzer filmleri tavsiye et
    recommendations = recommend(prototype_movie)
    
    # 6. Sonucu Flutter'a geri döndür
    return RecommendationResponse(
        emotion=emotion,
        prototype_movie=prototype_movie,
        recommendations=recommendations
    )

@app.get("/")
def read_root():
    return {"Merhaba": "MoodFlix API"}

# --- API'yi Çalıştırmak İçin ---
# Bu script'i doğrudan çalıştırdığımızda (debug için)
if __name__ == "__main__":
    # Bu satır, API'yi localhost:8000 adresinde başlatır.
    # Terminalden çalıştırmak için: uvicorn main:app --reload
    uvicorn.run(app, host="127.0.0.1", port=8000)