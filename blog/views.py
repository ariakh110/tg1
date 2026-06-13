from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .ai import AIContentSuggestionError, generate_content_suggestions
from .editorjs import render_editor_data
from .models import Category, FAQItem, FeaturedLoad, FeaturedLoadAlert, HomepageSlide, Landing, MediaAsset, Post, PostRevision, SiteSEOSettings
from .seo import analyze_post, build_article_schema, post_url, snapshot_post
from .serializers import (
    AdminPostSerializer,
    CategorySerializer,
    FAQItemSerializer,
    FeaturedLoadAlertSerializer,
    FeaturedLoadSerializer,
    HomepageSlideSerializer,
    LandingSerializer,
    MediaAssetSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostRevisionSerializer,
    SiteSEOSettingsSerializer,
)


class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 9
    page_size_query_param = 'page_size'
    max_page_size = 100


def public_posts():
    now = timezone.now()
    return (
        Post.objects.filter(robots_index=True)
        .filter(
            Q(status__in=['published', 'updated'], published_at__lte=now)
            | Q(status='scheduled', scheduled_at__lte=now)
        )
        .select_related('author')
        .prefetch_related('categories')
    )


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def get_queryset(self):
        queryset = public_posts()
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        return queryset.distinct()


class CategoryListView(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None
    permission_classes = [AllowAny]


class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None
    permission_classes = [IsAdminOrActiveAdminRole]


class AdminPostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('author').prefetch_related('categories')
    serializer_class = AdminPostSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAdminOrActiveAdminRole]

    def get_queryset(self):
        queryset = super().get_queryset()
        post_status = self.request.query_params.get('status')
        query = self.request.query_params.get('q')
        if post_status:
            queryset = queryset.filter(status=post_status)
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(slug__icontains=query)
                | Q(focus_keyword__icontains=query)
            )
        return queryset

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        post = self.get_object()
        scheduled_at = request.data.get('scheduled_at')
        if scheduled_at:
            serializer = self.get_serializer(post, data={'status': 'scheduled', 'scheduled_at': scheduled_at}, partial=True)
        else:
            serializer = self.get_serializer(
                post,
                data={'status': 'published', 'published_at': timezone.now(), 'scheduled_at': None},
                partial=True,
            )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analyze(self, request, pk=None):
        post = self.get_object()
        analysis = analyze_post(post)
        if post.seo_score != analysis['score']:
            Post.objects.filter(pk=post.pk).update(seo_score=analysis['score'])
        return Response(analysis)

    @action(detail=True, methods=['get'])
    def revisions(self, request, pk=None):
        revisions = self.get_object().revisions.select_related('created_by')
        return Response(PostRevisionSerializer(revisions, many=True).data)

    @action(detail=True, methods=['post'], url_path=r'revisions/(?P<revision_id>[^/.]+)/restore')
    def restore_revision(self, request, pk=None, revision_id=None):
        post = self.get_object()
        revision = post.revisions.get(pk=revision_id)
        serializer = self.get_serializer(post, data=revision.snapshot, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='ai-suggestions')
    def ai_suggestions(self, request):
        title = str(request.data.get('title', '')).strip()
        content = str(request.data.get('content', ''))
        if request.data.get('content_blocks') is not None:
            try:
                content = render_editor_data(request.data.get('content_blocks'))
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not title:
            return Response(
                {'detail': 'برای دریافت پیشنهاد، ابتدا عنوان مطلب را وارد کنید.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suggestions = generate_content_suggestions(title, content)
        except AIContentSuggestionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(suggestions)


class MediaAssetViewSet(viewsets.ModelViewSet):
    queryset = MediaAsset.objects.select_related('uploaded_by')
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAdminOrActiveAdminRole]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class HomepageSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HomepageSlide.objects.filter(is_active=True).order_by('sort_order', '-created_at')
    serializer_class = HomepageSlideSerializer
    pagination_class = None
    permission_classes = [AllowAny]


class AdminHomepageSlideViewSet(viewsets.ModelViewSet):
    queryset = HomepageSlide.objects.all().order_by('sort_order', '-created_at')
    serializer_class = HomepageSlideSerializer
    pagination_class = None
    permission_classes = [IsAdminOrActiveAdminRole]


class FeaturedLoadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FeaturedLoad.objects.filter(is_active=True).order_by('sort_order', '-created_at')
    serializer_class = FeaturedLoadSerializer
    pagination_class = None
    permission_classes = [AllowAny]


class AdminFeaturedLoadViewSet(viewsets.ModelViewSet):
    queryset = FeaturedLoad.objects.all().order_by('sort_order', '-created_at')
    serializer_class = FeaturedLoadSerializer
    pagination_class = None
    permission_classes = [IsAdminOrActiveAdminRole]


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQItem.objects.filter(is_active=True).order_by('category', 'sort_order', 'id')
    serializer_class = FAQItemSerializer
    pagination_class = None
    permission_classes = [AllowAny]


class AdminFAQViewSet(viewsets.ModelViewSet):
    queryset = FAQItem.objects.all().order_by('category', 'sort_order', 'id')
    serializer_class = FAQItemSerializer
    pagination_class = None
    permission_classes = [IsAdminOrActiveAdminRole]


class LandingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Landing.objects.filter(is_active=True).order_by('family', 'sort_order', 'id')
    serializer_class = LandingSerializer
    pagination_class = None
    permission_classes = [AllowAny]
    filterset_fields = ['family', 'slug']


class AdminLandingViewSet(viewsets.ModelViewSet):
    queryset = Landing.objects.all().order_by('family', 'sort_order', 'id')
    serializer_class = LandingSerializer
    pagination_class = None
    permission_classes = [IsAdminOrActiveAdminRole]


class FeaturedLoadAlertViewSet(viewsets.ModelViewSet):
    serializer_class = FeaturedLoadAlertSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return FeaturedLoadAlert.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class SEOAnalyzeView(APIView):
    permission_classes = [IsAdminOrActiveAdminRole]

    def get(self, request, slug):
        post = get_object_or_404(Post, slug=slug)
        return Response(analyze_post(post))


class SchemaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        post = get_object_or_404(public_posts(), slug=slug)
        return Response(build_article_schema(post))


class SitemapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        results = [
            {
                'url': post.canonical_url or post_url(post),
                'lastmod': post.updated_at.isoformat(),
                'changefreq': 'weekly',
                'priority': 0.8,
            }
            for post in public_posts()
        ]
        return Response({'results': results})


class RobotsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse(SiteSEOSettings.load().robots_txt, content_type='text/plain; charset=utf-8')


class AdminRobotsView(APIView):
    permission_classes = [IsAdminOrActiveAdminRole]

    def get(self, request):
        return Response(SiteSEOSettingsSerializer(SiteSEOSettings.load()).data)

    def patch(self, request):
        settings = SiteSEOSettings.load()
        serializer = SiteSEOSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
