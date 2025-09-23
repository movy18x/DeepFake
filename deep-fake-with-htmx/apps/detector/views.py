"""
Views لتطبيق كشف التلاعب مع دعم HTMX
"""
import os
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import UploadedMedia, DetectionHistory, UserStatistics, ProcessingStatus
from .tasks import run_enhanced_deepfake_detection_task
from .forms import UploadForm, DetectionSettingsForm


def home(request):
    """الصفحة الرئيسية"""
    context = {
        'total_detections': UploadedMedia.objects.filter(status=ProcessingStatus.DONE).count(),
        'total_users': UserStatistics.objects.count(),
        'average_confidence': UploadedMedia.objects.filter(
            status=ProcessingStatus.DONE,
            confidence_score__isnull=False
        ).aggregate(avg_confidence=Avg('confidence_score'))['avg_confidence'] or 0,
    }
    return render(request, 'pages/home.html', context)


@login_required
def upload_view(request):
    """صفحة رفع الملفات"""
    if request.method == 'POST':
        return handle_upload(request)

    form = UploadForm()
    context = {
        'form': form,
        'max_file_size_mb': settings.MAX_UPLOAD_SIZE_MB,
        'supported_formats': ['JPG', 'JPEG', 'PNG', 'WebP', 'MP4', 'MOV', 'AVI', 'MKV']
    }
    return render(request, 'pages/upload.html', context)


@login_required
@require_POST
def handle_upload(request):
    """معالجة رفع الملف مع HTMX"""
    form = UploadForm(request.POST, request.FILES)

    if not form.is_valid():
        # إرجاع أخطاء النموذج
        errors = []
        for field, field_errors in form.errors.items():
            for error in field_errors:
                errors.append(f"{form.fields[field].label}: {error}")

        if request.headers.get('HX-Request'):
            return render(request, 'partials/upload_error.html', {
                'errors': errors
            })
        else:
            for error in errors:
                messages.error(request, error)
            return redirect('detector:upload')

    # حفظ الملف
    uploaded_file = form.save(commit=False)
    uploaded_file.owner = request.user
    uploaded_file.original_filename = request.FILES['file'].name
    uploaded_file.file_size = request.FILES['file'].size

    # تحديد نوع الملف
    file_ext = os.path.splitext(uploaded_file.original_filename)[1].lower()
    if file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
        uploaded_file.kind = 'image'
    else:
        uploaded_file.kind = 'video'

    uploaded_file.save()

    # بدء مهمة الكشف
    enhanced = form.cleaned_data.get('enhanced', True)
    mode = form.cleaned_data.get('mode', 'balanced')

    # تحديث حالة الملف
    uploaded_file.status = ProcessingStatus.QUEUED
    uploaded_file.save()

    # تشغيل المهمة
    if enhanced:
        task = run_enhanced_deepfake_detection_task.delay(uploaded_file.id)
    else:
        from .tasks import run_deepfake_detection_task
        task = run_deepfake_detection_task.delay(uploaded_file.id)

    uploaded_file.task_id = task.id
    uploaded_file.save()

    if request.headers.get('HX-Request'):
        # إرجاع مكون التقدم للـ HTMX
        return render(request, 'components/progress_bar.html', {
            'upload_id': uploaded_file.id,
            'status': uploaded_file.status,
            'original_filename': uploaded_file.original_filename,
            'file_size_mb': uploaded_file.file_size_mb,
            'kind': uploaded_file.kind
        })
    else:
        messages.success(request, 'تم رفع الملف بنجاح وبدء عملية التحليل!')
        return redirect('detector:detail', pk=uploaded_file.id)


@login_required
def status_check(request, upload_id):
    """فحص حالة المعالجة - للتحديث التلقائي مع HTMX"""
    media = get_object_or_404(UploadedMedia, id=upload_id, owner=request.user)

    context = {
        'upload_id': media.id,
        'status': media.status,
        'original_filename': media.original_filename,
        'file_size_mb': media.file_size_mb,
        'kind': media.kind,
        'progress_percentage': 100 if media.status == ProcessingStatus.DONE else
        (75 if media.status == ProcessingStatus.PROCESSING else 25),
    }

    if media.status == ProcessingStatus.FAILED:
        context['error_message'] = media.details.get('error', 'حدث خطأ غير متوقع')

    return render(request, 'components/progress_bar.html', context)


@login_required
def detail_view(request, pk):
    """صفحة تفاصيل الملف"""
    media = get_object_or_404(UploadedMedia, id=pk, owner=request.user)

    context = {
        'media': media,
        'is_processing': media.is_processing,
        'is_completed': media.is_completed,
        'is_failed': media.is_failed,
    }

    if media.is_completed:
        # إضافة معلومات النتائج
        context.update({
            'debug_frames': media.debug_frames,
            'detection_history': DetectionHistory.objects.filter(media=media).order_by('-created_at')[:5]
        })

    return render(request, 'pages/detail.html', context)


@login_required
def result_view(request, pk):
    """صفحة النتائج - يمكن تحميلها جزئياً مع HTMX"""
    media = get_object_or_404(UploadedMedia, id=pk, owner=request.user)

    if not media.is_completed:
        if request.headers.get('HX-Request'):
            return render(request, 'partials/processing_message.html', {'media': media})
        else:
            messages.warning(request, 'لم تكتمل عملية التحليل بعد.')
            return redirect('detector:detail', pk=pk)

    context = {
        'media': media,
        'verdict_color': get_verdict_color(media.verdict),
        'confidence_percentage': int(media.confidence_score * 100) if media.confidence_score else 0,
        'show_debug_frames': len(media.debug_frames) > 0,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/result_card.html', context)
    else:
        return render(request, 'pages/result.html', context)


class MyFilesView(LoginRequiredMixin, ListView):
    """قائمة ملفات المستخدم"""
    model = UploadedMedia
    template_name = 'pages/my_files.html'
    context_object_name = 'files'
    paginate_by = 12

    def get_queryset(self):
        queryset = UploadedMedia.objects.filter(owner=self.request.user).order_by('-created_at')

        # البحث
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(original_filename__icontains=search_query) |
                Q(verdict__icontains=search_query)
            )

        # فلترة حسب الحالة
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # فلترة حسب النوع
        kind_filter = self.request.GET.get('kind')
        if kind_filter:
            queryset = queryset.filter(kind=kind_filter)

        # فلترة حسب الحكم
        verdict_filter = self.request.GET.get('verdict')
        if verdict_filter:
            queryset = queryset.filter(verdict=verdict_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'current_status': self.request.GET.get('status', ''),
            'current_kind': self.request.GET.get('kind', ''),
            'current_verdict': self.request.GET.get('verdict', ''),
            'status_choices': ProcessingStatus.choices,
            'kind_choices': [('image', 'صورة'), ('video', 'فيديو')],
            'verdict_choices': [
                ('highly_likely_real', 'حقيقي جداً'),
                ('likely_real', 'محتمل حقيقي'),
                ('uncertain', 'غير مؤكد'),
                ('suspicious', 'مشبوه'),
                ('likely_fake', 'محتمل مزيف'),
                ('highly_likely_fake', 'مزيف جداً'),
            ]
        })
        return context


@login_required
def delete_file(request, pk):
    """حذف ملف"""
    media = get_object_or_404(UploadedMedia, id=pk, owner=request.user)

    if request.method == 'POST':
        filename = media.original_filename
        media.delete()

        if request.headers.get('HX-Request'):
            messages.success(request, f'تم حذف الملف "{filename}" بنجاح.')
            return HttpResponse('')  # إزالة العنصر من القائمة
        else:
            messages.success(request, f'تم حذف الملف "{filename}" بنجاح.')
            return redirect('detector:my_files')

    return render(request, 'partials/delete_confirm.html', {'media': media})


@login_required
def debug_frames(request, pk):
    """عرض إطارات التصحيح"""
    media = get_object_or_404(UploadedMedia, id=pk, owner=request.user)

    if not media.is_completed or not media.debug_frames:
        raise Http404("إطارات التصحيح غير متوفرة")

    # تحضير مسارات الإطارات
    frames = []
    for frame_path in media.debug_frames:
        if os.path.exists(os.path.join(settings.MEDIA_ROOT, frame_path)):
            frames.append({
                'path': frame_path,
                'url': settings.MEDIA_URL + frame_path,
                'name': os.path.basename(frame_path)
            })

    context = {
        'media': media,
        'frames': frames
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/debug_frames.html', context)
    else:
        return render(request, 'pages/debug_frames.html', context)


@login_required
def statistics_view(request):
    """إحصائيات المستخدم"""
    stats, created = UserStatistics.objects.get_or_create(user=request.user)

    # إحصائيات إضافية
    recent_files = UploadedMedia.objects.filter(owner=request.user).order_by('-created_at')[:5]

    # إحصائيات شهرية
    from django.utils import timezone
    from datetime import timedelta

    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_stats = UploadedMedia.objects.filter(
        owner=request.user,
        created_at__gte=thirty_days_ago
    ).aggregate(
        total_this_month=Count('id'),
        completed_this_month=Count('id', filter=Q(status=ProcessingStatus.DONE))
    )

    context = {
        'stats': stats,
        'recent_files': recent_files,
        'monthly_stats': monthly_stats,
    }

    return render(request, 'pages/statistics.html', context)


@login_required
def retry_detection(request, pk):
    """إعادة محاولة الكشف للملفات الفاشلة"""
    media = get_object_or_404(UploadedMedia, id=pk, owner=request.user)

    if media.status != ProcessingStatus.FAILED:
        if request.headers.get('HX-Request'):
            return render(request, 'partials/error_message.html', {
                'message': 'يمكن إعادة المحاولة فقط للملفات الفاشلة'
            })
        else:
            messages.error(request, 'يمكن إعادة المحاولة فقط للملفات الفاشلة')
            return redirect('detector:detail', pk=pk)

    if request.method == 'POST':
        # إعادة تعيين الحالة
        media.status = ProcessingStatus.QUEUED
        media.task_id = None
        media.details = {}
        media.save()

        # تشغيل المهمة مرة أخرى
        task = run_enhanced_deepfake_detection_task.delay(media.id)
        media.task_id = task.id
        media.save()

        if request.headers.get('HX-Request'):
            return render(request, 'components/progress_bar.html', {
                'upload_id': media.id,
                'status': media.status,
                'original_filename': media.original_filename,
                'file_size_mb': media.file_size_mb,
                'kind': media.kind
            })
        else:
            messages.success(request, 'تم بدء إعادة المحاولة!')
            return redirect('detector:detail', pk=pk)

    return render(request, 'partials/retry_confirm.html', {'media': media})


# API Endpoints for HTMX
@login_required
@require_http_methods(["GET"])
def api_file_status(request, pk):
    """API endpoint لحالة الملف - للاستعلام السريع"""
    media = get_object_or_404(UploadedMedia, id=pk, owner=request.user)

    data = {
        'id': str(media.id),
        'status': media.status,
        'progress': get_progress_percentage(media.status),
        'is_completed': media.is_completed,
        'is_failed': media.is_failed,
    }

    if media.is_completed:
        data.update({
            'verdict': media.verdict,
            'confidence': media.confidence_score,
            'prob_fake': media.prob_fake,
        })

    if media.is_failed:
        data['error'] = media.details.get('error', 'خطأ غير محدد')

    return JsonResponse(data)


# Utility functions
def get_verdict_color(verdict):
    """إرجاع لون الحكم"""
    verdict_colors = {
        'highly_likely_real': 'success',
        'likely_real': 'success',
        'uncertain': 'warning',
        'suspicious': 'warning',
        'likely_fake': 'danger',
        'highly_likely_fake': 'danger',
    }
    return verdict_colors.get(verdict, 'secondary')


def get_progress_percentage(status):
    """حساب نسبة التقدم حسب الحالة"""
    progress_map = {
        ProcessingStatus.UPLOADED: 10,
        ProcessingStatus.QUEUED: 25,
        ProcessingStatus.PROCESSING: 75,
        ProcessingStatus.DONE: 100,
        ProcessingStatus.FAILED: 0,
        ProcessingStatus.CANCELLED: 0,
    }
    return progress_map.get(status, 0)


# Error handlers
def handler404(request, exception):
    """معالج خطأ 404"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """معالج خطأ 500"""
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    """معالج خطأ 403"""
    return render(request, 'errors/403.html', status=403)