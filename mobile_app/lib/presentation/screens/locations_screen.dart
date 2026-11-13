import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/responsive_layout.dart';
import '../../core/utils/url_launcher_helper.dart';
import '../../models/location_item_model.dart';
import '../../providers/location_provider.dart';

class LocationsScreen extends StatefulWidget {
  final String? initialQuery;
  final String? initialKind;

  const LocationsScreen({
    super.key,
    this.initialQuery,
    this.initialKind,
  });

  @override
  State<LocationsScreen> createState() => _LocationsScreenState();
}

class _LocationsScreenState extends State<LocationsScreen> {
  late final TextEditingController _searchController;
  final List<String> _quickLocations = [
    'Đà Nẵng',
    'Hồ Chí Minh',
    'Hà Nội',
    'Huế',
    'Cần Thơ',
    'Hải Phòng',
  ];

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(text: widget.initialQuery ?? '');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<LocationProvider>();
      if (widget.initialKind != null) {
        provider.setKind(widget.initialKind!);
      }
      if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
        provider.searchLocations(
          query: widget.initialQuery,
          kind: widget.initialKind,
        );
      } else if (provider.locations.isEmpty && provider.currentQuery.isEmpty) {
        // Pre-fill a standard search for immediate responsiveness
        _searchController.text = 'Đà Nẵng';
        provider.searchLocations(query: 'Đà Nẵng');
      } else if (provider.currentQuery.isNotEmpty) {
        _searchController.text = provider.currentQuery;
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _handleSearch() {
    final query = _searchController.text.trim();
    if (query.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vui lòng nhập thành phố, quận/huyện hoặc khu vực cần tìm.')),
      );
      return;
    }
    context.read<LocationProvider>().searchLocations(query: query);
  }

  @override
  Widget build(BuildContext context) {
    final locProvider = context.watch<LocationProvider>();
    final isDesktop = ResponsiveLayout.isDesktop(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.place_rounded, color: AppColors.gold, size: 22),
            SizedBox(width: 8),
            Text('Nhà Sách & Thư Viện'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Làm mới kết quả',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: locProvider.isLoading ? null : () => locProvider.retryLastSearch(),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Search Header Box
              _buildSearchHeader(context, locProvider, isDesktop),

              // Content Area: Loading, Error, Empty, or Results
              Expanded(
                child: _buildContent(context, locProvider),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSearchHeader(
    BuildContext context,
    LocationProvider provider,
    bool isDesktop,
  ) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.map_rounded, size: 20, color: AppColors.navy),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Tra cứu dữ liệu địa điểm thực tế từ Google Maps',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppColors.navyDark,
                  ),
                ),
              ),
              if (provider.locations.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.navyLight,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${provider.locations.length} địa điểm',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppColors.navyDark,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),

          // Search Row: Input + Search Button
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _handleSearch(),
                  decoration: InputDecoration(
                    hintText: 'Nhập tỉnh/thành, quận/huyện (VD: Đà Nẵng, Huế, Cầu Giấy...)',
                    hintStyle: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
                    prefixIcon: const Icon(Icons.search_rounded, color: AppColors.navy),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear_rounded, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              setState(() {});
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: AppColors.surfaceVariant,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppColors.border),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppColors.border),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppColors.navy, width: 1.5),
                    ),
                  ),
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: 10),
              ElevatedButton.icon(
                onPressed: provider.isLoading ? null : _handleSearch,
                icon: provider.isLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.search_rounded, size: 18),
                label: const Text('Tìm kiếm'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.navy,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  elevation: 0,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Filter Controls Row: Kind Selector + Quick Location Chips
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              // Kind Filter Chips
              _buildKindChip(
                label: '📚 Nhà sách',
                kind: 'bookstore',
                isSelected: provider.selectedKind == 'bookstore',
                onSelected: () {
                  provider.setKind('bookstore');
                  _handleSearch();
                },
              ),
              _buildKindChip(
                label: '🏛️ Thư viện',
                kind: 'library',
                isSelected: provider.selectedKind == 'library',
                onSelected: () {
                  provider.setKind('library');
                  _handleSearch();
                },
              ),
              _buildKindChip(
                label: '🌐 Tất cả',
                kind: 'all',
                isSelected: provider.selectedKind == 'all',
                onSelected: () {
                  provider.setKind('all');
                  _handleSearch();
                },
              ),

              const SizedBox(width: 8),
              const Text(
                'Gợi ý:',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary,
                ),
              ),

              // Quick Location Chips
              ..._quickLocations.map((loc) {
                final isCurrent = _searchController.text.trim().toLowerCase() == loc.toLowerCase();
                return ActionChip(
                  label: Text(
                    loc,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                      color: isCurrent ? AppColors.navyDark : AppColors.textPrimary,
                    ),
                  ),
                  backgroundColor: isCurrent ? AppColors.goldLight : AppColors.surfaceVariant,
                  side: BorderSide(
                    color: isCurrent ? AppColors.gold : AppColors.border,
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
                  onPressed: () {
                    _searchController.text = loc;
                    setState(() {});
                    context.read<LocationProvider>().searchLocations(query: loc);
                  },
                );
              }),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildKindChip({
    required String label,
    required String kind,
    required bool isSelected,
    required VoidCallback onSelected,
  }) {
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => onSelected(),
      selectedColor: AppColors.gold,
      backgroundColor: AppColors.surfaceVariant,
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
        color: isSelected ? AppColors.navyDark : AppColors.textPrimary,
      ),
      side: BorderSide(
        color: isSelected ? AppColors.goldDark : AppColors.border,
      ),
    );
  }

  Widget _buildContent(BuildContext context, LocationProvider provider) {
    if (provider.isLoading) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(color: AppColors.navy),
            const SizedBox(height: 16),
            Text(
              'Đang tra cứu dữ liệu địa điểm thực tế từ Google Maps...',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: Colors.grey.shade700,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Thông tin nhà sách & thư viện thật kèm địa chỉ và hotline',
              style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }

    if (provider.errorMessage != null && provider.locations.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off_rounded, size: 56, color: AppColors.error),
              const SizedBox(height: 16),
              const Text(
                'Không thể tải dữ liệu địa điểm',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.navyDark),
              ),
              const SizedBox(height: 8),
              Text(
                provider.errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => provider.retryLastSearch(),
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Thử lại'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.navy,
                  foregroundColor: Colors.white,
                ),
              ),
              if (provider.fallbackUrls.isNotEmpty) ...[
                const SizedBox(height: 16),
                _buildFallbackUrlsRow(provider.fallbackUrls),
              ],
            ],
          ),
        ),
      );
    }

    if (provider.locations.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.place_outlined, size: 56, color: AppColors.textSecondary),
              const SizedBox(height: 16),
              Text(
                provider.currentQuery.isNotEmpty
                    ? 'Không tìm thấy địa điểm nào tại "${provider.currentQuery}"'
                    : 'Nhập khu vực và nhấn "Tìm kiếm" để bắt đầu tra cứu',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.navyDark),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              const Text(
                'Thử tìm với tên thành phố lớn (Đà Nẵng, Huế, Hà Nội, TP.HCM...) hoặc mở trực tiếp trên Google Maps.',
                style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                textAlign: TextAlign.center,
              ),
              if (provider.fallbackUrls.isNotEmpty) ...[
                const SizedBox(height: 16),
                _buildFallbackUrlsRow(provider.fallbackUrls),
              ],
            ],
          ),
        ),
      );
    }

    // Results List
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: provider.locations.length + 1, // +1 for footer fallback
      itemBuilder: (context, index) {
        if (index == provider.locations.length) {
          return _buildResultsFooter(provider);
        }
        final item = provider.locations[index];
        return _buildLocationCard(context, item);
      },
    );
  }

  Widget _buildLocationCard(BuildContext context, LocationItemModel item) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title & Rating Row
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.navyLight,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.storefront_rounded,
                    color: AppColors.navyDark,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: AppColors.navyDark,
                        ),
                      ),
                      if (item.rating > 0) ...[
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(Icons.star_rounded, size: 16, color: AppColors.goldDark),
                            const SizedBox(width: 4),
                            Text(
                              '${item.rating.toStringAsFixed(1)} / 5.0',
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navyDark,
                              ),
                            ),
                            if (item.reviews > 0) ...[
                              const SizedBox(width: 6),
                              Text(
                                '(${item.reviews} lượt đánh giá)',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Address
            if (item.address.isNotEmpty) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.place_outlined, size: 16, color: AppColors.error),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item.address,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textPrimary,
                        height: 1.35,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],

            // Open State / Hours
            if (item.openState.isNotEmpty || item.hours.isNotEmpty) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.access_time_rounded, size: 16, color: AppColors.success),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item.openState.isNotEmpty ? item.openState : item.hours,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: AppColors.success,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],

            // Phone Hotline
            if (item.phone.isNotEmpty) ...[
              Row(
                children: [
                  const Icon(Icons.phone_outlined, size: 16, color: AppColors.navy),
                  const SizedBox(width: 8),
                  Text(
                    'Hotline: ${item.phone}',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.navyDark,
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: () {
                      Clipboard.setData(ClipboardData(text: item.phone));
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Đã sao chép số điện thoại: ${item.phone}')),
                      );
                    },
                    child: const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                      child: Text(
                        'Sao chép',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.navy,
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
            ],

            const Divider(height: 16),

            // Action Buttons: Directions, Open Maps, Website
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                // Button 1: Directions
                ElevatedButton.icon(
                  onPressed: () {
                    final url = item.directionsUrl.isNotEmpty
                        ? item.directionsUrl
                        : item.googleMapsUrl;
                    if (url.isNotEmpty) {
                      UrlLauncherHelper.launchUrlString(url);
                    }
                  },
                  icon: const Icon(Icons.directions_rounded, size: 16),
                  label: const Text('Chỉ đường trên Google Maps'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.navy,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                ),

                // Button 2: Open Google Maps
                OutlinedButton.icon(
                  onPressed: () {
                    final url = item.googleMapsUrl.isNotEmpty
                        ? item.googleMapsUrl
                        : item.directionsUrl;
                    if (url.isNotEmpty) {
                      UrlLauncherHelper.launchUrlString(url);
                    }
                  },
                  icon: const Icon(Icons.map_outlined, size: 16),
                  label: const Text('Xem trên Bản đồ'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.navyDark,
                    side: const BorderSide(color: AppColors.border),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                ),

                // Button 3: Website (if present)
                if (item.website.isNotEmpty)
                  OutlinedButton.icon(
                    onPressed: () {
                      UrlLauncherHelper.launchUrlString(item.website);
                    },
                    icon: const Icon(Icons.language_rounded, size: 16),
                    label: const Text('Ghé thăm Website'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.navy,
                      side: const BorderSide(color: AppColors.navy),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFallbackUrlsRow(Map<String, String> fallbackUrls) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: [
        if (fallbackUrls.containsKey('google_maps_bookstores'))
          OutlinedButton.icon(
            onPressed: () {
              UrlLauncherHelper.launchUrlString(fallbackUrls['google_maps_bookstores']!);
            },
            icon: const Icon(Icons.search_rounded, size: 16),
            label: const Text('Tìm nhà sách trên Google Maps'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.navyDark,
              side: const BorderSide(color: AppColors.navy),
            ),
          ),
        if (fallbackUrls.containsKey('google_maps_libraries'))
          OutlinedButton.icon(
            onPressed: () {
              UrlLauncherHelper.launchUrlString(fallbackUrls['google_maps_libraries']!);
            },
            icon: const Icon(Icons.search_rounded, size: 16),
            label: const Text('Tìm thư viện trên Google Maps'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.navyDark,
              side: const BorderSide(color: AppColors.navy),
            ),
          ),
      ],
    );
  }

  Widget _buildResultsFooter(LocationProvider provider) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20.0),
      child: Center(
        child: Column(
          children: [
            const Text(
              'Cần tìm thêm địa điểm hoặc ở các khu vực khác?',
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 8),
            _buildFallbackUrlsRow(provider.fallbackUrls),
          ],
        ),
      ),
    );
  }
}

