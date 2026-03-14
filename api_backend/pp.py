import nltk
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import pandas as pd
import ast


try:
    movies_df = pd.read_csv('tmdb_5000_movies.csv')
    credits_df = pd.read_csv('tmdb_5000_credits.csv')
    
except FileNotFoundError:
    print("HATA: CSV dosyaları 'api_backend' klasöründe bulunamadı.")
    print("Lütfen 'tmdb_5000_movies.csv' ve 'tmdb_5000_credits.csv' dosyalarının doğru yerde olduğundan emin olun.")
    exit()
#iki data frame i birleştirme    
movies = movies_df.merge(credits_df, left_on='id', right_on='movie_id')

#önişleme

movies = movies[['movie_id', 'title_x', 'overview', 'genres', 'keywords', 'cast', 'crew']]
movies.rename(columns={'title_x': 'title'}, inplace=True)

#NaN değerlerin kontrolü ve temizliği

movies.dropna(inplace=True)

#karmaşık metin sütunlarını işleme

def convert(text_obj):
    L =[]
    try:
        for i in ast.literal_eval(text_obj):
            L.append(i['name'])
    except(ValueError, SyntaxError):
        pass
    return L

def convert_cast(text_obj):
    """Sadece ilk 3 başrol oyuncusunu alır."""
    L = []
    counter = 0
    try:
        for i in ast.literal_eval(text_obj):
            if counter < 3:
                L.append(i['name'])
                counter += 1
            else:
                break
    except (ValueError, SyntaxError):
        pass
    return L

def fetch_director(text_obj):
    """Sadece yönetmenin adını çeker."""
    L = []
    try:
        for i in ast.literal_eval(text_obj):
            if i['job'] == 'Director':
                L.append(i['name'])
                break # Sadece bir yönetmen (ilki) yeterli
    except (ValueError, SyntaxError):
        pass
    return L

print("karmaşık metin sütunları işleniyor.")

#fonksiyonları dataframe uygulama
movies['genres'] = movies['genres'].apply(convert)
movies['keywords'] = movies['keywords'].apply(convert)
movies['cast'] = movies['cast'].apply(convert_cast)
movies['crew']=movies['crew'].apply(fetch_director)

#overview sütununu metin liste çevirme
movies['overview'] = movies['overview'].apply(lambda x: x.split())

#boşllukları kaldırma

movies['genres'] = movies['genres'].apply(lambda x: [i.replace(" ","") for i in x])
movies['keywords'] = movies['keywords'].apply(lambda x: [i.replace(" ","") for i in x])
movies['cast'] = movies['cast'].apply(lambda x: [i.replace(" ","") for i in x])
movies['crew'] = movies['crew'].apply(lambda x: [i.replace(" ","") for i in x])

#tüm içerik verileri tek bi tags sütununda birleşitirme
movies['tags'] = movies['overview'] + movies['genres'] + movies['keywords'] + movies['cast'] + movies['crew']

#yeni df oluşturma
new_df = movies[['movie_id','title','tags']]

#tags sütunundaki lsteyi tek string haline getirme
new_df['tags']=new_df['tags'].apply(lambda x: " ".join(x))
new_df['tags'] = new_df['tags'].apply(lambda x: x.lower())

print("temizlenmiş tags sütunu oluşturuldu.")
print(new_df.head())

cv = CountVectorizer(max_features=5000, stop_words='english')

#tags sütununu vektör matrisine dönüştürme
vectors = cv.fit_transform(new_df['tags']).toarray()
print(f"Vektör matrisinin boyutu: {vectors.shape}")


# Filmler arası kosinüs benzerliğini hesaplama
# Bu, hangi filmin hangi filme ne kadar benzediğini gösteren bir matris verir
similarity = cosine_similarity(vectors)
print(f"Benzerlik matrisinin boyutu: {similarity.shape}")

print("Benzerlik matrisi (cosine similarity) hesaplandı.")

pickle.dump(new_df.to_dict(), open('movies_list.pkl', 'wb'))
pickle.dump(similarity, open('similarity.pkl', 'wb'))

print("--- Faz 1 Tamamlandı: 'movies_list.pkl' ve 'similarity.pkl' dosyaları 'api_backend' klasörüne kaydedildi. ---")













