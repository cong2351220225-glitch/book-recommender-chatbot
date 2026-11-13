import 'package:flutter/material.dart';
import '../models/author_model.dart';
import '../repositories/author_repository.dart';

class AuthorProvider extends ChangeNotifier {
  final AuthorRepository _authorRepository;

  List<AuthorModel> _authors = [];
  bool _isLoading = false;
  String? _errorMessage;
  String _searchQuery = '';

  AuthorModel? _selectedAuthor;
  bool _isLoadingDetail = false;
  String? _detailError;

  AuthorProvider({AuthorRepository? authorRepository})
      : _authorRepository = authorRepository ?? AuthorRepository();

  List<AuthorModel> get authors => _authors;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String get searchQuery => _searchQuery;

  AuthorModel? get selectedAuthor => _selectedAuthor;
  bool get isLoadingDetail => _isLoadingDetail;
  String? get detailError => _detailError;

  Future<void> fetchAuthors({String? query}) async {
    _isLoading = true;
    _errorMessage = null;
    if (query != null) _searchQuery = query;
    notifyListeners();

    try {
      _authors = await _authorRepository.getAuthors(query: _searchQuery);
      _errorMessage = null;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchAuthorDetail(String authorId) async {
    _isLoadingDetail = true;
    _detailError = null;
    _selectedAuthor = null;
    notifyListeners();

    try {
      _selectedAuthor = await _authorRepository.getAuthorDetail(authorId);
      _detailError = null;
    } catch (e) {
      _detailError = e.toString();
    } finally {
      _isLoadingDetail = false;
      notifyListeners();
    }
  }
}

