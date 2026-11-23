# Rota Arama

Birimlerin yollarını nasıl bulduğunu değiştiren modüller için ortak bir yapı taşıdır. Tek başına oyunda hiçbir şeyi değiştirmez.

Smarter Pathing (suikastçılar için kestirme yol) ve Gatehouse Fixes (kapılardan geçen rotalara ilişkin kurallar), bir birime yeni bir hedef verildiğinde oyunun nasıl rota aradığını değiştirir. Rota Arama bu iki modülün birlikte çalışmasını sağlar. Her modül kendi kuralını buraya ekler ve her kural, hangi birim için rota aranıyorsa o birimi dikkate alır. Bu iki modülün yalnızca Rota Arama’yı bağımlılık olarak belirten sürümleri bu modülü kullanır ve otomatik olarak kurar.
