import 'package:flutter/material.dart';
import '../models/genre_model.dart';
import '../repositories/genre_repository.dart';

class GenreProvider extends ChangeNotifier {
  final GenreRepository _genreRepository;

  List<GenreModel> _genres = [];
  bool _isLoading = false;
  String? _errorMessage;

  GenreProvider({GenreRepository? genreRepository})
      : _genreRepository = genreRepository ?? GenreRepository();

  List<GenreModel> get genres => _genres;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> fetchGenres() async {
    if (_genres.isNotEmpty) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _genres = await _genreRepository.getGenres();
      _errorMessage = null;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

