class LocationItemModel {
  final String title;
  final String address;
  final double rating;
  final int reviews;
  final String phone;
  final String openState;
  final String hours;
  final double? latitude;
  final double? longitude;
  final String googleMapsUrl;
  final String directionsUrl;
  final String thumbnail;
  final String website;

  LocationItemModel({
    required this.title,
    this.address = '',
    this.rating = 0.0,
    this.reviews = 0,
    this.phone = '',
    this.openState = '',
    this.hours = '',
    this.latitude,
    this.longitude,
    this.googleMapsUrl = '',
    this.directionsUrl = '',
    this.thumbnail = '',
    this.website = '',
  });

  factory LocationItemModel.fromJson(Map<String, dynamic> json) {
    return LocationItemModel(
      title: json['title']?.toString() ?? json['name']?.toString() ?? 'Địa điểm',
      address: json['address']?.toString() ?? '',
      rating: (json['rating'] as num?)?.toDouble() ?? 0.0,
      reviews: (json['reviews'] as num?)?.toInt() ?? 0,
      phone: json['phone']?.toString() ?? '',
      openState: json['open_state']?.toString() ?? '',
      hours: json['hours']?.toString() ?? '',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      googleMapsUrl: json['google_maps_url']?.toString() ?? json['maps_url']?.toString() ?? '',
      directionsUrl: json['directions_url']?.toString() ?? '',
      thumbnail: json['thumbnail']?.toString() ?? '',
      website: json['website']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'address': address,
      'rating': rating,
      'reviews': reviews,
      'phone': phone,
      'open_state': openState,
      'hours': hours,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      'google_maps_url': googleMapsUrl,
      'directions_url': directionsUrl,
      'thumbnail': thumbnail,
      'website': website,
    };
  }
}

class LocationSearchResponseModel {
  final String location;
  final String kind;
  final List<LocationItemModel> results;
  final Map<String, String> fallbackUrls;

  LocationSearchResponseModel({
    required this.location,
    required this.kind,
    required this.results,
    required this.fallbackUrls,
  });

  factory LocationSearchResponseModel.fromJson(Map<String, dynamic> json) {
    final rawResults = json['results'] as List<dynamic>? ?? [];
    final results = rawResults
        .map((e) => LocationItemModel.fromJson(e as Map<String, dynamic>))
        .toList();

    final rawFallback = json['fallback_urls'] as Map<String, dynamic>? ?? {};
    final fallbackUrls = rawFallback.map(
      (k, v) => MapEntry(k.toString(), v?.toString() ?? ''),
    );

    return LocationSearchResponseModel(
      location: json['location']?.toString() ?? '',
      kind: json['kind']?.toString() ?? '',
      results: results,
      fallbackUrls: fallbackUrls,
    );
  }
}

