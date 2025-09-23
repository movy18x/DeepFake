# apps/detector/forms.py
"""
نماذج تطبيق الكشف
"""
from django import forms
from django.core.validators import FileExtensionValidator
from django.conf import settings
from .models import UploadedMedia


class UploadForm(forms.ModelForm):
    """نموذج رفع الملفات"""

    # خيارات التحليل
    enhanced = forms.BooleanField(
        required=False,
        initial=True,
        label='التحليل المحسن',
        help_text='يشمل التحليل الجنائي المتقدم لدقة أعلى'
    )

    MODE_CHOICES = [
        ('fast', 'سريع - أقل دقة لكن أسرع'),
        ('balanced', 'متوازن - توازن بين السرعة والدقة'),
        ('high_quality', 'عالي الجودة - أعلى دقة لكن أبطأ'),
    ]

    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        initial='balanced',
        label='نمط المعالجة',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = UploadedMedia
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,video/*',
                'id': 'file-input',
            })
        }
        labels = {
            'file': 'اختر الملف'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة المدققات
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov', 'avi', 'mkv']
        self.fields['file'].validators = [
            FileExtensionValidator(allowed_extensions=allowed_extensions)
        ]

        # إضافة خصائص HTML5
        max_size_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 100)
        self.fields['file'].widget.attrs.update({
            'data-max-size': max_size_mb * 1024 * 1024,  # بالبايت
            'data-allowed-types': ','.join(allowed_extensions),
        })

    def clean_file(self):
        file = self.cleaned_data.get('file')

        if file:
            # فحص حجم الملف
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 100) * 1024 * 1024
            if file.size > max_size:
                raise forms.ValidationError(
                    f'حجم الملف كبير جداً. الحد الأقصى {settings.MAX_UPLOAD_SIZE_MB}MB'
                )

            # فحص نوع الملف
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp',
                             'video/mp4', 'video/quicktime', 'video/avi', 'video/x-msvideo']

            if file.content_type not in allowed_types:
                raise forms.ValidationError('نوع الملف غير مدعوم')

        return file


class DetectionSettingsForm(forms.Form):
    """نموذج إعدادات الكشف"""

    # إعدادات عامة
    enable_forensic_analysis = forms.BooleanField(
        required=False,
        initial=True,
        label='تفعيل التحليل الجنائي',
        help_text='يحلل الضوضاء والضغط والإضاءة للكشف عن التلاعب'
    )

    forensic_weight = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.3,
        label='وزن التحليل الجنائي',
        help_text='نسبة تأثير التحليل الجنائي على النتيجة النهائية',
        widget=forms.NumberInput(attrs={
            'step': '0.1',
            'class': 'form-range',
        })
    )

    # إعدادات الوجوه
    face_crop_margin = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.2,
        label='هامش قص الوجه',
        help_text='مساحة إضافية حول الوجه المكتشف',
        widget=forms.NumberInput(attrs={
            'step': '0.05',
            'class': 'form-range',
        })
    )

    min_face_size = forms.IntegerField(
        min_value=20,
        max_value=200,
        initial=40,
        label='أصغر حجم وجه',
        help_text='أصغر حجم وجه بالبكسل للكشف'
    )

    # إعدادات العتبات
    decision_threshold = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.6,
        label='عتبة القرار',
        help_text='النقطة الفاصلة بين حقيقي ومزيف',
        widget=forms.NumberInput(attrs={
            'step': '0.05',
            'class': 'form-range',
        })
    )

    high_confidence_threshold = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.8,
        label='عتبة الثقة العالية',
        help_text='النقطة للأحكام عالية الثقة',
        widget=forms.NumberInput(attrs={
            'step': '0.05',
            'class': 'form-range',
        })
    )

    # إعدادات التصحيح
    debug_save_frames = forms.BooleanField(
        required=False,
        initial=True,
        label='حفظ إطارات التصحيح',
        help_text='حفظ الإطارات المحللة للمراجعة'
    )

    debug_max_frames = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=8,
        label='عدد إطارات التصحيح',
        help_text='أقصى عدد إطارات للحفظ'
    )


class SearchForm(forms.Form):
    """نموذج البحث في الملفات"""

    search = forms.CharField(
        required=False,
        max_length=100,
        label='البحث',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ابحث في أسماء الملفات...',
            'hx-get': '',  # سيتم تعيينه في القالب
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#files-list',
            'autocomplete': 'off',
        })
    )

    STATUS_CHOICES = [
        ('', 'جميع الحالات'),
        ('uploaded', 'مرفوع'),
        ('queued', 'في الطابور'),
        ('processing', 'قيد المعالجة'),
        ('done', 'مكتمل'),
        ('failed', 'فشل'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='الحالة',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#files-list',
        })
    )

    KIND_CHOICES = [
        ('', 'جميع الأنواع'),
        ('image', 'صور'),
        ('video', 'فيديو'),
    ]

    kind = forms.ChoiceField(
        choices=KIND_CHOICES,
        required=False,
        label='النوع',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#files-list',
        })
    )

    VERDICT_CHOICES = [
        ('', 'جميع الأحكام'),
        ('highly_likely_real', 'حقيقي جداً'),
        ('likely_real', 'محتمل حقيقي'),
        ('uncertain', 'غير مؤكد'),
        ('suspicious', 'مشبوه'),
        ('likely_fake', 'محتمل مزيف'),
        ('highly_likely_fake', 'مزيف جداً'),
    ]

    verdict = forms.ChoiceField(
        choices=VERDICT_CHOICES,
        required=False,
        label='الحكم',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#files-list',
        })
    )


class FeedbackForm(forms.Form):
    """نموذج التغذية الراجعة على النتائج"""

    RATING_CHOICES = [
        (5, 'ممتاز'),
        (4, 'جيد جداً'),
        (3, 'جيد'),
        (2, 'مقبول'),
        (1, 'سيء'),
    ]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label='تقييم دقة النتيجة',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )

    is_correct = forms.BooleanField(
        required=False,
        label='هل النتيجة صحيحة؟',
        help_text='هل توافق على النتيجة التي توصل إليها النظام؟'
    )

    comments = forms.CharField(
        required=False,
        max_length=500,
        label='تعليقات إضافية',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'شاركنا رأيك لتحسين النظام...'
        })
    )

    # معلومات خفية
    media_id = forms.UUIDField(widget=forms.HiddenInput())

    def save(self, user):
        """حفظ التغذية الراجعة"""
        # يمكن حفظها في نموذج منفصل أو كجزء من تفاصيل الملف
        from .models import UploadedMedia

        media = UploadedMedia.objects.get(id=self.cleaned_data['media_id'])

        feedback_data = {
            'rating': int(self.cleaned_data['rating']),
            'is_correct': self.cleaned_data['is_correct'],
            'comments': self.cleaned_data['comments'],
            'user': user.username,
            'timestamp': timezone.now().isoformat()
        }

        # إضافة التغذية الراجعة للتفاصيل
        if 'user_feedback' not in media.details:
            media.details['user_feedback'] = []

        media.details['user_feedback'].append(feedback_data)
        media.save(update_fields=['details'])

        return media