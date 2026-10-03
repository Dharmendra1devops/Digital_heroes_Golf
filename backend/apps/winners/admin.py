from django.contrib import admin

from apps.winners.models import DrawWinner, Payout, WinnerProof


class WinnerProofInline(admin.TabularInline):
    model = WinnerProof
    extra = 0
    readonly_fields = ('bucket', 'object_path', 'review_status', 'submitted_at', 'reviewed_by', 'reviewed_at', 'review_reason')


class PayoutInline(admin.TabularInline):
    model = Payout
    extra = 0
    readonly_fields = ('attempt_number', 'amount_minor', 'currency', 'status', 'provider_payout_id', 'paid_at', 'failure_reason')


@admin.register(DrawWinner)
class DrawWinnerAdmin(admin.ModelAdmin):
    list_display = ('entry', 'match_count', 'prize_amount_minor', 'currency', 'verification_status', 'reviewed_at')
    list_filter = ('verification_status', 'match_count', 'currency')
    search_fields = ('entry__user__email',)
    inlines = (WinnerProofInline, PayoutInline)
    readonly_fields = tuple(field.name for field in DrawWinner._meta.fields)


@admin.register(WinnerProof)
class WinnerProofAdmin(admin.ModelAdmin):
    list_display = ('winner', 'review_status', 'submitted_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('review_status',)
    readonly_fields = tuple(field.name for field in WinnerProof._meta.fields)


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('winner', 'attempt_number', 'status', 'amount_minor', 'currency', 'paid_at')
    list_filter = ('status', 'currency')
    readonly_fields = tuple(field.name for field in Payout._meta.fields)
