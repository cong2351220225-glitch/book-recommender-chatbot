class GenreModel {
  final String genreId;
  final String name;
  final String description;
  final String icon;
  final int bookCount;

  GenreModel({
    required this.genreId,
    required this.name,
    this.description = '',
    this.icon = '',
    this.bookCount = 0,
  });

  factory GenreModel.fromJson(Map<String, dynamic> json) {
    return GenreModel(
      genreId: json['genre_id']?.toString() ?? '',
      name: json['name']?.toString() ?? json['genre']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      icon: json['icon']?.toString() ?? 'menu_book',
      bookCount: (json['book_count'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'genre_id': genreId,
      'name': name,
      'description': description,
      'icon': icon,
      'book_count': bookCount,
    };
  }
}

