import 'book_model.dart';

class AuthorModel {
  final String authorId;
  final String name;
  final String bio;
  final dynamic birthYear;
  final dynamic deathYear;
  final String nationality;
  final int workCount;
  final List<String> genres;
  final List<BookModel> books;

  AuthorModel({
    required this.authorId,
    required this.name,
    this.bio = '',
    this.birthYear,
    this.deathYear,
    this.nationality = '',
    this.workCount = 0,
    this.genres = const [],
    this.books = const [],
  });

  String get lifespan {
    if (birthYear != null && deathYear != null && deathYear.toString().isNotEmpty) {
      return '$birthYear – $deathYear';
    }
    if (birthYear != null) {
      return 'Sinh $birthYear';
    }
    return '';
  }

  factory AuthorModel.fromJson(Map<String, dynamic> json) {
    final rawGenres = json['genres'] as List<dynamic>? ?? [];
    final genres = rawGenres.map((e) => e.toString()).toList();

    final rawBooks = json['books'] as List<dynamic>? ?? [];
    final books = rawBooks
        .map((b) => BookModel.fromJson(b as Map<String, dynamic>))
        .toList();

    return AuthorModel(
      authorId: json['author_id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Chưa rõ tác giả',
      bio: json['bio']?.toString() ?? '',
      birthYear: json['birth_year'],
      deathYear: json['death_year'],
      nationality: json['nationality']?.toString() ?? '',
      workCount: (json['work_count'] as num?)?.toInt() ?? books.length,
      genres: genres,
      books: books,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'author_id': authorId,
      'name': name,
      'bio': bio,
      'birth_year': birthYear,
      'death_year': deathYear,
      'nationality': nationality,
      'work_count': workCount,
      'genres': genres,
    };
  }
}

