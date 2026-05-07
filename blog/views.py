
from django.utils import timezone
from rest_framework import pagination, viewsets

from .models import Post, Category
from .serializers import PostListSerializer, PostDetailSerializer, CategorySerializer

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 9
    page_size_query_param = 'page_size'
    max_page_size = 100

class PostViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def get_queryset(self):
        queryset = (
            Post.objects.filter(status='published', published_at__lte=timezone.now())
            .select_related('author')
            .prefetch_related('categories')
        )
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        return queryset.distinct()

class CategoryListView(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None # برای نمایش در منو نیازی به صفحه‌بندی نیست
