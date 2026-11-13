import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/responsive_layout.dart';
import '../../providers/auth_provider.dart';
import '../../providers/navigation_provider.dart';
import '../screens/home_screen.dart';
import '../screens/books_catalog_screen.dart';
import '../screens/my_bookshelf_screen.dart';
import '../screens/ai_chat_screen.dart';
import '../screens/locations_screen.dart';
import '../screens/authors_screen.dart';
import '../screens/genres_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/ai_crawler_screen.dart';

class AppScaffold extends StatelessWidget {
  const AppScaffold({super.key});

  static const List<Widget> _screens = [
    HomeScreen(),
    BooksCatalogScreen(),
    MyBookshelfScreen(),
    AiChatScreen(),
    LocationsScreen(),
    AuthorsScreen(),
    GenresScreen(),
    ProfileScreen(),
    AiCrawlerScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final navProvider = context.watch<NavigationProvider>();
    final currentIndex = navProvider.currentIndex;

    return ResponsiveLayout(
      mobile: _buildMobileScaffold(context, currentIndex, navProvider),
      tablet: _buildMobileScaffold(context, currentIndex, navProvider),
      desktop: _buildDesktopScaffold(context, currentIndex, navProvider),
    );
  }

  Widget _buildMobileScaffold(
    BuildContext context,
    int currentIndex,
    NavigationProvider navProvider,
  ) {
    return Scaffold(
      body: IndexedStack(
        index: currentIndex >= _screens.length ? 0 : currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex >= 8 ? 7 : currentIndex,
        onDestinationSelected: navProvider.setIndex,
        backgroundColor: Colors.white,
        elevation: 3,
        indicatorColor: AppColors.gold.withOpacity(0.25),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded, color: AppColors.navyDark),
            label: 'Trang chủ',
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book_rounded, color: AppColors.navyDark),
            label: 'Kho sách',
          ),
          NavigationDestination(
            icon: Icon(Icons.collections_bookmark_outlined),
            selectedIcon: Icon(Icons.collections_bookmark_rounded, color: AppColors.navyDark),
            label: 'Tủ sách',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_awesome_outlined),
            selectedIcon: Icon(Icons.auto_awesome, color: AppColors.navyDark),
            label: 'Trợ lý AI',
          ),
          NavigationDestination(
            icon: Icon(Icons.place_outlined),
            selectedIcon: Icon(Icons.place_rounded, color: AppColors.navyDark),
            label: 'Địa điểm',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline_rounded),
            selectedIcon: Icon(Icons.people_rounded, color: AppColors.navyDark),
            label: 'Tác giả',
          ),
          NavigationDestination(
            icon: Icon(Icons.category_outlined),
            selectedIcon: Icon(Icons.category_rounded, color: AppColors.navyDark),
            label: 'Thể loại',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(Icons.person_rounded, color: AppColors.navyDark),
            label: 'Hồ sơ',
          ),
        ],
      ),
    );
  }

  Widget _buildDesktopScaffold(
    BuildContext context,
    int currentIndex,
    NavigationProvider navProvider,
  ) {
    final authProvider = context.watch<AuthProvider>();
    final user = authProvider.currentUser;

    return Scaffold(
      body: Row(
        children: [
          // Desktop Left Sidebar
          Container(
            width: 250,
            color: AppColors.navyDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Brand Header
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppColors.gold,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(
                          Icons.local_library_rounded,
                          color: AppColors.navyDark,
                          size: 22,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'THƯ VIỆN SỐ AI',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.6,
                            ),
                          ),
                          Text(
                            'Multi-Platform Library',
                            style: TextStyle(
                              color: AppColors.goldLight,
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                const Divider(color: Color(0xFF1E3A5F), height: 1),
                const SizedBox(height: 12),

                // Navigation Items
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    children: [
                      _buildSidebarItem(
                        icon: Icons.home_rounded,
                        label: 'Trang chủ',
                        isSelected: currentIndex == NavigationProvider.tabHome,
                        onTap: () => navProvider.goToHome(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.menu_book_rounded,
                        label: 'Kho sách',
                        isSelected: currentIndex == NavigationProvider.tabBooksCatalog,
                        onTap: () => navProvider.goToCatalog(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.collections_bookmark_rounded,
                        label: 'Tủ sách cá nhân',
                        isSelected: currentIndex == NavigationProvider.tabBookshelf,
                        onTap: () => navProvider.goToBookshelf(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.auto_awesome,
                        label: 'Trợ lý AI (RAG)',
                        isSelected: currentIndex == NavigationProvider.tabAiChat,
                        onTap: () => navProvider.goToAiChat(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.place_rounded,
                        label: 'Nhà sách & Thư viện',
                        isSelected: currentIndex == NavigationProvider.tabLocations,
                        onTap: () => navProvider.goToLocations(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.people_rounded,
                        label: 'Tác giả',
                        isSelected: currentIndex == NavigationProvider.tabAuthors,
                        onTap: () => navProvider.goToAuthors(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.category_rounded,
                        label: 'Thể loại',
                        isSelected: currentIndex == NavigationProvider.tabGenres,
                        onTap: () => navProvider.goToGenres(),
                      ),
                      _buildSidebarItem(
                        icon: Icons.person_rounded,
                        label: 'Hồ sơ người dùng',
                        isSelected: currentIndex == NavigationProvider.tabProfile,
                        onTap: () => navProvider.goToProfile(),
                      ),
                      if (user?.isAdmin ?? false) ...[
                        const Padding(
                          padding: EdgeInsets.fromLTRB(16, 16, 16, 6),
                          child: Text(
                            'QUẢN TRỊ VIÊN',
                            style: TextStyle(
                              color: AppColors.goldLight,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ),
                        _buildSidebarItem(
                          icon: Icons.hub_rounded,
                          label: 'AI Crawler & ChromaDB',
                          isSelected: currentIndex == NavigationProvider.tabAiCrawler,
                          onTap: () => navProvider.goToAiCrawler(),
                        ),
                      ],
                    ],
                  ),
                ),

                // User profile card at bottom
                const Divider(color: Color(0xFF1E3A5F), height: 1),
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 18,
                        backgroundColor: AppColors.navyLight,
                        child: Text(
                          (user?.username.isNotEmpty ?? false)
                              ? user!.username[0].toUpperCase()
                              : '?',
                          style: const TextStyle(
                            color: AppColors.gold,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              user?.username ?? 'Khách',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Text(
                              user?.role.toUpperCase() ?? 'GUEST',
                              style: const TextStyle(
                                color: AppColors.goldLight,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Main Content View
          Expanded(
            child: IndexedStack(
              index: currentIndex,
              children: _screens,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebarItem({
    required IconData icon,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4.0),
      child: Material(
        color: isSelected ? AppColors.navy : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 20,
                  color: isSelected ? AppColors.gold : AppColors.textOnNavyMuted,
                ),
                const SizedBox(width: 12),
                Text(
                  label,
                  style: TextStyle(
                    color: isSelected ? Colors.white : AppColors.textOnNavyMuted,
                    fontSize: 14,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
