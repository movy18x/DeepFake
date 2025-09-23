"""
نماذج تطبيق كشف التلاعب
"""
import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


def upload_to_user_directory(instance, filename):
    """رفع الملفات إلى مجلد المستخدم"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex}.{ext}'
    return f'uploads/{instance.owner.id}/{filename}'


class MediaKind(models.TextChoices):
    """أنواع الوسائط المدعومة"""
    IMAGE = 'image', _('صورة')
    VIDEO = 'video', _('فيديو')


class ProcessingStatus(models.TextChoices):
    """حالات المعالجة"""
    UPLOADED = 'uploaded', _('مرفوعة')
    QUEUED = 'queued', _('في الطابور')
    PROCESSING = 'processing', _('قيد المعالجة')
    DONE = 'done', _('مكتملة')
    FAILED = 'failed', _('فشلت')
    CANCELLED = 'cancelled', _('ملغية')


class DetectionVerdict(models.TextChoices):
    """أحكام الكشف"""
    HIGHLY_LIKELY_REAL = 'highly_likely_real', _('على الأرجح حقيقي')
    LIKELY_REAL = 'likely_real', _('محتمل حقيقي')
    UNCERTAIN = 'uncertain', _('غير مؤكد')
    SUSPICIOUS = 'suspicious', _('مشبوه')
    LIKELY_FAKE = 'likely_fake', _('محتمل مزيف')
    HIGHLY_LIKELY_FAKE = 'highly_likely_fake', _('على الأرجح مزيف')


class UploadedMedia(models.Model):
    """نموذج الوسائط المرفوعة"""

    # معلومات أساسية
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_media',
        verbose_name=_('المالك')
    )

    # الملف
    file = models.FileField(
        upload_to=upload_to_user_directory,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov', 'avi', 'mkv']
            )
        ],
        verbose_name=_('الملف')
    )

    # معلومات الملف
    original_filename = models.CharField(max_length=255, verbose_name=_('اسم الملف الأصلي'))
    file_size = models.PositiveBigIntegerField(verbose_name=_('حجم الملف (بايت)'))
    kind = models.CharField(
        max_length=10,
        choices=MediaKind.choices,
        verbose_name=_('نوع الوسائط')
    )

    # معلومات المعالجة
    status = models.CharField(
        max_length=15,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
        verbose_name=_('الحالة')
    )
    task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('معرف المهمة'))

    # النتائج
    prob_fake = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('احتمال التزييف')
    )
    verdict = models.CharField(
        max_length=25,
        choices=DetectionVerdict.choices,
        blank=True,
        verbose_name=_('الحكم')
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('درجة الثقة')
    )

    # معلومات التحليل
    frame_count = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('عدد الإطارات'))
    faces_detected = models.PositiveIntegerField(default=0, verbose_name=_('عدد الوجوه المكتشفة'))

    # نتائج التحليل المفصل
    deepfake_probability = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('احتمال الديب فيك')
    )
    forensic_probability = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('احتمال التحليل الجنائي')
    )

    # معلومات إضافية (JSON)
    details = models.JSONField(default=dict, blank=True, verbose_name=_('التفاصيل'))

    # معلومات زمنية
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))

    # معلومات المعالجة
    processing_started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('بدء المعالجة'))
    processing_completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('انتهاء المعالجة'))
    processing_time_seconds = models.FloatField(null=True, blank=True, verbose_name=_('وقت المعالجة (ثواني)'))

    class Meta:
        verbose_name = _('وسائط مرفوعة')
        verbose_name_plural = _('الوسائط المرفوعة')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['verdict']),
            models.Index(fields=['prob_fake']),
        ]

    def __str__(self):
        return f"{self.original_filename} - {self.get_status_display()}"

    @property
    def file_size_mb(self):
        """حجم الملف بالميجابايت"""
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0

    @property
    def is_processing(self):
        """هل الملف قيد المعالجة"""
        return self.status in [ProcessingStatus.QUEUED, ProcessingStatus.PROCESSING]

    @property
    def is_completed(self):
        """هل المعالجة مكتملة"""
        return self.status == ProcessingStatus.DONE

    @property
    def is_failed(self):
        """هل فشلت المعالجة"""
        return self.status == ProcessingStatus.FAILED

    @property
    def debug_frames(self):
        """إطارات التصحيح"""
        return self.details.get('debug_frames', [])

    @property
    def detection_type(self):
        """نوع الكشف المستخدم"""
        return self.details.get('detection_type', 'unknown')

    @property
    def model_info(self):
        """معلومات النموذج"""
        return self.details.get('model_info', {})

    def get_absolute_url(self):
        """رابط الملف"""
        return reverse('detector:detail', kwargs={'pk': self.pk})

    def get_result_url(self):
        """رابط النتيجة"""
        return reverse('detector:result', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """حفظ مخصص"""
        # تعيين اسم الملف الأصلي إذا لم يكن محدداً
        if not self.original_filename and self.file:
            self.original_filename = os.path.basename(self.file.name)

        # تعيين حجم الملف
        if self.file and not self.file_size:
            self.file_size = self.file.size

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """حذف مخصص - يحذف الملف من التخزين"""
        if self.file:
            try:
                self.file.delete(save=False)
            except Exception:
                pass  # تجاهل أخطاء حذف الملف

        super().delete(*args, **kwargs)


class DetectionHistory(models.Model):
    """سجل عمليات الكشف"""

    media = models.ForeignKey(
        UploadedMedia,
        on_delete=models.CASCADE,
        related_name='detection_history',
        verbose_name=_('الوسائط')
    )

    # معلومات النسخة
    version = models.CharField(max_length=50, verbose_name=_('إصدار النظام'))
    detection_type = models.CharField(max_length=50, verbose_name=_('نوع الكشف'))
    model_backend = models.CharField(max_length=50, verbose_name=_('نوع النموذج'))

    # النتائج
    probability = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('الاحتمال')
    )
    verdict = models.CharField(
        max_length=25,
        choices=DetectionVerdict.choices,
        verbose_name=_('الحكم')
    )
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('الثقة')
    )

    # معلومات إضافية
    processing_time = models.FloatField(verbose_name=_('وقت المعالجة'))
    settings_used = models.JSONField(default=dict, verbose_name=_('الإعدادات المستخدمة'))

    # معلومات زمنية
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))

    class Meta:
        verbose_name = _('سجل كشف')
        verbose_name_plural = _('سجل عمليات الكشف')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['media', 'created_at']),
            models.Index(fields=['detection_type']),
        ]

    def __str__(self):
        return f"{self.media.original_filename} - {self.detection_type} - {self.verdict}"


class UserStatistics(models.Model):
    """إحصائيات المستخدم"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='statistics',
        verbose_name=_('المستخدم')
    )

    # إحصائيات الرفع
    total_uploads = models.PositiveIntegerField(default=0, verbose_name=_('إجمالي الرفعات'))
    total_images = models.PositiveIntegerField(default=0, verbose_name=_('إجمالي الصور'))
    total_videos = models.PositiveIntegerField(default=0, verbose_name=_('إجمالي الفيديوهات'))

    # إحصائيات الكشف
    total_detections = models.PositiveIntegerField(default=0, verbose_name=_('إجمالي عمليات الكشف'))
    fake_detected = models.PositiveIntegerField(default=0, verbose_name=_('مزيفة مكتشفة'))
    real_detected = models.PositiveIntegerField(default=0, verbose_name=_('حقيقية مكتشفة'))
    uncertain_results = models.PositiveIntegerField(default=0, verbose_name=_('نتائج غير مؤكدة'))

    # إحصائيات الاستخدام
    total_processing_time = models.FloatField(default=0, verbose_name=_('إجمالي وقت المعالجة'))
    average_confidence = models.FloatField(default=0, verbose_name=_('متوسط الثقة'))

    # معلومات زمنية
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name=_('آخر نشاط'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        verbose_name = _('إحصائيات مستخدم')
        verbose_name_plural = _('إحصائيات المستخدمين')

    def __str__(self):
        return f"إحصائيات {self.user.username}"

    def update_statistics(self, media_instance):
        """تحديث الإحصائيات بناءً على ملف جديد"""
        self.total_uploads += 1

        if media_instance.kind == MediaKind.IMAGE:
            self.total_images += 1
        elif media_instance.kind == MediaKind.VIDEO:
            self.total_videos += 1

        if media_instance.is_completed:
            self.total_detections += 1

            if media_instance.verdict in [DetectionVerdict.LIKELY_FAKE, DetectionVerdict.HIGHLY_LIKELY_FAKE]:
                self.fake_detected += 1
            elif media_instance.verdict in [DetectionVerdict.LIKELY_REAL, DetectionVerdict.HIGHLY_LIKELY_REAL]:
                self.real_detected += 1
            else:
                self.uncertain_results += 1

            if media_instance.processing_time_seconds:
                self.total_processing_time += media_instance.processing_time_seconds

            if media_instance.confidence_score:
                # حساب متوسط الثقة الجديد
                total_confidence = self.average_confidence * (
                            self.total_detections - 1) + media_instance.confidence_score
                self.average_confidence = total_confidence / self.total_detections

        self.last_activity = timezone.now()
        self.save()

    @property
    def success_rate(self):
        """معدل النجاح (الكشف المؤكد)"""
        if self.total_detections == 0:
            return 0
        return (self.fake_detected + self.real_detected) / self.total_detections * 100

    @property
    def average_processing_time(self):
        """متوسط وقت المعالجة"""
        if self.total_detections == 0:
            return 0
        return self.total_processing_time / self.total_detections


# إشارات Django لتحديث الإحصائيات تلقائياً
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender=UploadedMedia)
def update_user_statistics(sender, instance, created, **kwargs):
    """تحديث إحصائيات المستخدم عند إنشاء أو تحديث ملف"""
    stats, created_stats = UserStatistics.objects.get_or_create(user=instance.owner)
    if created or instance.status == ProcessingStatus.DONE:
        stats.update_statistics(instance)