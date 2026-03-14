import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_card_swiper/flutter_card_swiper.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:shared_preferences/shared_preferences.dart';

// --- SABİTLER ---
// Android Emülatör için: 10.0.2.2, Gerçek cihaz için: Bilgisayarın IP'si
const String backendUrl = 'http://10.0.2.2:8000/recommend';

// BURAYA DİKKAT: Posterlerin görünmesi için TMDB API Key'ini buraya yapıştır.
// Yoksa sadece renkli kutular görünür.
const String tmdbApiKey = '40a776b0563d50429f3324cd9f7635bd'; 

void main() {
  runApp(const MoodFlixApp());
}

class MoodFlixApp extends StatelessWidget {
  const MoodFlixApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MoodFlix',
      theme: ThemeData.dark().copyWith(
        primaryColor: Colors.deepPurple,
        scaffoldBackgroundColor: const Color(0xFF121212),
        colorScheme: const ColorScheme.dark(
          primary: Colors.deepPurple,
          secondary: Colors.amber,
        ),
      ),
      home: const InputScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

// --- 1. SAYFA: GİRİŞ EKRANI ---
class InputScreen extends StatefulWidget {
  const InputScreen({super.key});

  @override
  State<InputScreen> createState() => _InputScreenState();
}

class _InputScreenState extends State<InputScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;

  Future<void> _getRecommendations() async {
    if (_controller.text.isEmpty) return;

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse(backendUrl),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        body: jsonEncode({'text': _controller.text}),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        List<String> movies = List<String>.from(data['recommendations']);
        
        if (mounted) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => SwipeScreen(
                emotion: data['emotion'],
                movies: movies,
              ),
            ),
          );
        }
      } else {
        _showError('Sunucu hatası: ${response.statusCode}');
      }
    } catch (e) {
      _showError('Bağlantı hatası. Backend çalışıyor mu?');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MoodFlix 🎬'),
        actions: [
          IconButton(
            icon: const Icon(Icons.bookmark),
            onPressed: () => Navigator.push(
              context, 
              MaterialPageRoute(builder: (context) => const LibraryScreen())
            ),
          )
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                "Bugün nasıl hissediyorsun?",
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 30),
              TextField(
                controller: _controller,
                style: const TextStyle(fontSize: 18),
                decoration: InputDecoration(
                  hintText: 'Örn: Sınavdan 100 aldım, uçuyorum!',
                  filled: true,
                  fillColor: Colors.grey[900],
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.all(20),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 30),
              SizedBox(
                width: double.infinity,
                height: 60,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _getRecommendations,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepPurple,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  child: _isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text("Filmleri Getir", style: TextStyle(fontSize: 20, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// --- 2. SAYFA: SWIPE (KAYDIRMA) EKRANI ---
class SwipeScreen extends StatefulWidget {
  final String emotion;
  final List<String> movies;

  const SwipeScreen({super.key, required this.emotion, required this.movies});

  @override
  State<SwipeScreen> createState() => _SwipeScreenState();
}

class _SwipeScreenState extends State<SwipeScreen> {
  final CardSwiperController controller = CardSwiperController();

  // Beğenilen filmi kaydetme fonksiyonu
  Future<void> _saveMovie(String movieName) async {
    final prefs = await SharedPreferences.getInstance();
    List<String> savedMovies = prefs.getStringList('saved_movies') ?? [];
    
    if (!savedMovies.contains(movieName)) {
      savedMovies.add(movieName);
      await prefs.setStringList('saved_movies', savedMovies);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$movieName kütüphaneye eklendi! 💖'), 
            duration: const Duration(seconds: 1),
            backgroundColor: Colors.green,
          ),
        );
      }
    }
  }

  // TMDB'den poster URL'i bulma
  Future<String?> _fetchPosterUrl(String movieName) async {
    if (tmdbApiKey == 'BURAYA_TMDB_API_KEY_YAZILACAK') return null;
    
    try {
      final url = Uri.parse(
          'https://api.themoviedb.org/3/search/movie?api_key=$tmdbApiKey&query=$movieName');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['results'] != null && data['results'].length > 0) {
          final posterPath = data['results'][0]['poster_path'];
          if (posterPath != null) {
            return 'https://image.tmdb.org/t/p/w500$posterPath';
          }
        }
      }
    } catch (e) {
      print("Poster hatası: $e");
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Modun: ${widget.emotion}")),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: CardSwiper(
                controller: controller,
                cardsCount: widget.movies.length,
                
                // --- AYARLAR ---
                isLoop: false, // Döngüyü kapat
                onEnd: () {    // Bittiğinde çalışacak kod
                   ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("Tüm önerileri inceledin! Ana sayfaya dönülüyor..."),
                      duration: Duration(seconds: 2),
                    ),
                  );
                  Future.delayed(const Duration(milliseconds: 1000), () {
                    if (mounted) Navigator.pop(context);
                  });
                },
                // --------------

                onSwipe: (previousIndex, currentIndex, direction) {
                  if (direction == CardSwiperDirection.right) {
                    _saveMovie(widget.movies[previousIndex]);
                  }
                  return true;
                },
                cardBuilder: (context, index, percentThresholdX, percentThresholdY) {
                  final movieName = widget.movies[index];
                  return _buildMovieCard(movieName);
                },
              ),
            ),
            const Padding(
              padding: EdgeInsets.all(20.0),
              child: Text("Beğenmek için Sağa 👉, Geçmek için Sola 👈", 
                style: TextStyle(color: Colors.white54)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMovieCard(String movieName) {
    return FutureBuilder<String?>(
      future: _fetchPosterUrl(movieName),
      builder: (context, snapshot) {
        final posterUrl = snapshot.data;
        
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            color: Colors.grey[850],
            boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 10)],
          ),
          alignment: Alignment.center,
          child: Stack(
            fit: StackFit.expand,
            children: [
              if (posterUrl != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: CachedNetworkImage(
                    imageUrl: posterUrl,
                    fit: BoxFit.cover,
                    placeholder: (context, url) => const Center(child: CircularProgressIndicator()),
                    errorWidget: (context, url, error) => const Icon(Icons.error),
                  ),
                )
              else
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(20),
                    gradient: const LinearGradient(
                      colors: [Colors.deepPurple, Colors.blueAccent],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                  child: const Icon(Icons.movie, size: 100, color: Colors.white24),
                ),

              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    borderRadius: const BorderRadius.vertical(bottom: Radius.circular(20)),
                    gradient: LinearGradient(
                      colors: [Colors.black.withOpacity(0.8), Colors.transparent],
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                    ),
                  ),
                  child: Text(
                    movieName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

// --- 3. SAYFA: KÜTÜPHANEM ---
class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  List<String> _savedMovies = [];

  @override
  void initState() {
    super.initState();
    _loadSavedMovies();
  }

  Future<void> _loadSavedMovies() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _savedMovies = prefs.getStringList('saved_movies') ?? [];
    });
  }

  Future<void> _removeMovie(String movieName) async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _savedMovies.remove(movieName);
    });
    await prefs.setStringList('saved_movies', _savedMovies);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Kütüphanem 📚")),
      body: _savedMovies.isEmpty
          ? const Center(child: Text("Henüz hiç film beğenmedin."))
          : ListView.builder(
              itemCount: _savedMovies.length,
              itemBuilder: (context, index) {
                final movie = _savedMovies[index];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  color: Colors.grey[900],
                  child: ListTile(
                    leading: const Icon(Icons.favorite, color: Colors.redAccent),
                    title: Text(movie, style: const TextStyle(color: Colors.white)),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete, color: Colors.grey),
                      onPressed: () => _removeMovie(movie),
                    ),
                  ),
                );
              },
            ),
    );
  }
}