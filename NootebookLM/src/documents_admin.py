"""
Interface d'administration Django pour l'app documents.
Fournit une interface riche pour gérer les documents et chunks.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .models import SourceDocument, DocumentChunk, QueryLog


# ========================================
# INLINE ADMINS
# ========================================

class DocumentChunkInline(admin.TabularInline):
    """
    Affiche les chunks d'un document dans la page de détail.
    """
    model = DocumentChunk
    extra = 0
    fields = ('chunk_index', 'content_preview', 'content_length', 'page_number', 'created_at')
    readonly_fields = ('chunk_index', 'content_preview', 'content_length', 'page_number', 'created_at')
    can_delete = False
    
    def content_preview(self, obj):
        """Affiche un aperçu du contenu du chunk."""
        if obj.content:
            preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
            return preview
        return '-'
    content_preview.short_description = 'Aperçu du contenu'
    
    def has_add_permission(self, request, obj=None):
        """Empêche l'ajout manuel de chunks (créés automatiquement)."""
        return False


# ========================================
# SOURCE DOCUMENT ADMIN
# ========================================

@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les documents sources.
    """
    
    list_display = (
        'title_with_icon',
        'user',
        'file_type_badge',
        'file_size_human',
        'status_badge',
        'chunks_count',
        'progress_bar',
        'created_at_formatted',
        'actions_buttons'
    )
    
    list_filter = (
        'processing_status',
        'file_type',
        'created_at',
        'user'
    )
    
    search_fields = (
        'title',
        'user__username',
        'user__email',
        'file_hash'
    )
    
    readonly_fields = (
        'file_hash',
        'file_size',
        'file_type',
        'processing_status',
        'processing_error',
        'total_pages',
        'total_chunks',
        'total_characters',
        'extracted_metadata',
        'created_at',
        'updated_at',
        'processed_at',
        'file_preview'
    )
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'user', 'file', 'file_preview')
        }),
        ('Métadonnées du fichier', {
            'fields': ('file_type', 'file_size', 'file_hash')
        }),
        ('Traitement', {
            'fields': (
                'processing_status',
                'processing_error',
                'total_pages',
                'total_chunks',
                'total_characters'
            )
        }),
        ('Métadonnées extraites', {
            'fields': ('extracted_metadata',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [DocumentChunkInline]
    
    actions = ['reprocess_documents', 'delete_chunks', 'mark_as_failed']
    
    # ========================================
    # MÉTHODES PERSONNALISÉES POUR L'AFFICHAGE
    # ========================================
    
    def title_with_icon(self, obj):
        """Affiche le titre avec une icône selon le type de fichier."""
        icon = '📄'
        if 'pdf' in obj.file_type.lower():
            icon = '📕'
        elif 'text' in obj.file_type.lower():
            icon = '📝'
        
        return format_html(
            '<strong>{} {}</strong>',
            icon,
            obj.title
        )
    title_with_icon.short_description = 'Document'
    title_with_icon.admin_order_field = 'title'
    
    def file_type_badge(self, obj):
        """Affiche le type de fichier avec un badge coloré."""
        color = '#3498db'
        if 'pdf' in obj.file_type.lower():
            color = '#e74c3c'
        elif 'text' in obj.file_type.lower():
            color = '#2ecc71'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 0.85em;">{}</span>',
            color,
            obj.file_type.split('/')[-1].upper()
        )
    file_type_badge.short_description = 'Type'
    
    def file_size_human(self, obj):
        """Affiche la taille du fichier en format lisible."""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_human.short_description = 'Taille'
    file_size_human.admin_order_field = 'file_size'
    
    def status_badge(self, obj):
        """Affiche le statut avec un badge coloré."""
        colors = {
            'PENDING': '#f39c12',
            'PROCESSING': '#3498db',
            'COMPLETED': '#2ecc71',
            'FAILED': '#e74c3c'
        }
        
        icons = {
            'PENDING': '⏳',
            'PROCESSING': '⚙️',
            'COMPLETED': '✅',
            'FAILED': '❌'
        }
        
        color = colors.get(obj.processing_status, '#95a5a6')
        icon = icons.get(obj.processing_status, '❓')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 4px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_processing_status_display()
        )
    status_badge.short_description = 'Statut'
    status_badge.admin_order_field = 'processing_status'
    
    def chunks_count(self, obj):
        """Affiche le nombre de chunks avec un lien."""
        count = obj.chunks.count()
        if count > 0:
            url = reverse('admin:documents_documentchunk_changelist') + f'?source_document__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="font-weight: bold; color: #3498db;">{} chunks</a>',
                url,
                count
            )
        return format_html('<span style="color: #95a5a6;">0 chunks</span>')
    chunks_count.short_description = 'Chunks'
    
    def progress_bar(self, obj):
        """Affiche une barre de progression."""
        if obj.processing_status == 'COMPLETED':
            percentage = 100
            color = '#2ecc71'
        elif obj.processing_status == 'PROCESSING':
            percentage = 50
            color = '#3498db'
        elif obj.processing_status == 'FAILED':
            percentage = 0
            color = '#e74c3c'
        else:
            percentage = 0
            color = '#f39c12'
        
        return format_html(
            '<div style="width: 100px; background-color: #ecf0f1; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; height: 20px; '
            'text-align: center; color: white; font-size: 0.75em; line-height: 20px;">'
            '{}%</div></div>',
            percentage,
            color,
            percentage
        )
    progress_bar.short_description = 'Progression'
    
    def created_at_formatted(self, obj):
        """Affiche la date de création formatée."""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Créé le'
    created_at_formatted.admin_order_field = 'created_at'
    
    def actions_buttons(self, obj):
        """Affiche des boutons d'action personnalisés."""
        buttons = []
        
        if obj.processing_status == 'FAILED':
            buttons.append(
                '<a href="#" onclick="alert(\'Utilisez l\'action Retraiter\');" '
                'style="background-color: #f39c12; color: white; padding: 2px 8px; '
                'border-radius: 3px; text-decoration: none; font-size: 0.85em;">🔄 Réessayer</a>'
            )
        
        if obj.file:
            buttons.append(
                f'<a href="{obj.file.url}" target="_blank" '
                'style="background-color: #3498db; color: white; padding: 2px 8px; '
                'border-radius: 3px; text-decoration: none; font-size: 0.85em;">📥 Télécharger</a>'
            )
        
        return format_html(' '.join(buttons))
    actions_buttons.short_description = 'Actions'
    
    def file_preview(self, obj):
        """Affiche un aperçu du fichier."""
        if obj.file:
            return format_html(
                '<div style="margin: 10px 0;">'
                '<strong>Fichier :</strong> {}<br>'
                '<strong>Taille :</strong> {}<br>'
                '<strong>Hash :</strong> <code>{}</code><br>'
                '<a href="{}" target="_blank" style="color: #3498db; font-weight: bold;">📥 Télécharger le fichier</a>'
                '</div>',
                obj.file.name,
                self.file_size_human(obj),
                obj.file_hash[:16] + '...',
                obj.file.url
            )
        return '-'
    file_preview.short_description = 'Aperçu du fichier'
    
    # ========================================
    # ACTIONS PERSONNALISÉES
    # ========================================
    
    def reprocess_documents(self, request, queryset):
        """Relance le traitement des documents sélectionnés."""
        from .tasks import reprocess_document
        
        count = 0
        for doc in queryset:
            reprocess_document.delay(doc.id)
            count += 1
        
        self.message_user(
            request,
            f"{count} document(s) envoyé(s) pour retraitement."
        )
    reprocess_documents.short_description = "🔄 Retraiter les documents sélectionnés"
    
    def delete_chunks(self, request, queryset):
        """Supprime tous les chunks des documents sélectionnés."""
        total_chunks = 0
        for doc in queryset:
            count = doc.chunks.count()
            doc.chunks.all().delete()
            total_chunks += count
        
        self.message_user(
            request,
            f"{total_chunks} chunk(s) supprimé(s) pour {queryset.count()} document(s)."
        )
    delete_chunks.short_description = "🗑️ Supprimer les chunks"
    
    def mark_as_failed(self, request, queryset):
        """Marque les documents comme échoués."""
        count = queryset.update(processing_status='FAILED')
        self.message_user(
            request,
            f"{count} document(s) marqué(s) comme échoué(s)."
        )
    mark_as_failed.short_description = "❌ Marquer comme échoué"
    
    # ========================================
    # STATISTIQUES DANS LE CHANGELIST
    # ========================================
    
    def changelist_view(self, request, extra_context=None):
        """Ajoute des statistiques au haut de la liste."""
        extra_context = extra_context or {}
        
        # Statistiques globales
        queryset = self.get_queryset(request)
        extra_context['total_documents'] = queryset.count()
        extra_context['pending_count'] = queryset.filter(processing_status='PENDING').count()
        extra_context['processing_count'] = queryset.filter(processing_status='PROCESSING').count()
        extra_context['completed_count'] = queryset.filter(processing_status='COMPLETED').count()
        extra_context['failed_count'] = queryset.filter(processing_status='FAILED').count()
        
        return super().changelist_view(request, extra_context=extra_context)


# ========================================
# DOCUMENT CHUNK ADMIN
# ========================================

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les chunks de documents.
    """
    
    list_display = (
        'chunk_preview',
        'source_document_link',
        'chunk_index',
        'page_number',
        'content_length_badge',
        'created_at_formatted'
    )
    
    list_filter = (
        'source_document',
        'page_number',
        'created_at'
    )
    
    search_fields = (
        'content',
        'source_document__title',
        'source_document__user__username'
    )
    
    readonly_fields = (
        'source_document',
        'content',
        'content_length',
        'embedding',
        'chunk_index',
        'page_number',
        'metadata',
        'created_at',
        'embedding_preview'
    )
    
    fieldsets = (
        ('Informations', {
            'fields': ('source_document', 'chunk_index', 'page_number')
        }),
        ('Contenu', {
            'fields': ('content', 'content_length')
        }),
        ('Embedding', {
            'fields': ('embedding_preview',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('metadata', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def chunk_preview(self, obj):
        """Affiche un aperçu du chunk."""
        preview = obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
        return format_html(
            '<div style="max-width: 300px; white-space: nowrap; overflow: hidden; '
            'text-overflow: ellipsis;" title="{}">{}</div>',
            obj.content,
            preview
        )
    chunk_preview.short_description = 'Contenu'
    
    def source_document_link(self, obj):
        """Lien vers le document source."""
        url = reverse('admin:documents_sourcedocument_change', args=[obj.source_document.id])
        return format_html(
            '<a href="{}" style="color: #3498db; font-weight: bold;">{}</a>',
            url,
            obj.source_document.title
        )
    source_document_link.short_description = 'Document'
    source_document_link.admin_order_field = 'source_document'
    
    def content_length_badge(self, obj):
        """Badge pour la longueur du contenu."""
        color = '#2ecc71' if obj.content_length < 500 else '#f39c12'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 0.85em;">{} chars</span>',
            color,
            obj.content_length
        )
    content_length_badge.short_description = 'Longueur'
    content_length_badge.admin_order_field = 'content_length'
    
    def created_at_formatted(self, obj):
        """Date de création formatée."""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Créé le'
    created_at_formatted.admin_order_field = 'created_at'
    
    def embedding_preview(self, obj):
        """Affiche un aperçu de l'embedding."""
        if obj.embedding:
            preview = str(obj.embedding)[:200] + '...'
            return format_html(
                '<div style="background-color: #ecf0f1; padding: 10px; border-radius: 5px; '
                'font-family: monospace; font-size: 0.85em; max-height: 200px; overflow-y: auto;">'
                '{}</div>',
                preview
            )
        return '-'
    embedding_preview.short_description = 'Aperçu de l\'embedding'
    
    def has_add_permission(self, request):
        """Empêche l'ajout manuel de chunks."""
        return False


# ========================================
# QUERY LOG ADMIN
# ========================================

@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les logs de requêtes RAG.
    """
    
    list_display = (
        'query_preview',
        'user',
        'documents_count',
        'chunks_count_badge',
        'response_time_badge',
        'tokens_badge',
        'rating_stars',
        'created_at_formatted'
    )
    
    list_filter = (
        'user',
        'user_rating',
        'created_at',
        'retrieved_chunks_count'
    )
    
    search_fields = (
        'query_text',
        'response_text',
        'user__username'
    )
    
    readonly_fields = (
        'user',
        'query_text',
        'response_text',
        'retrieved_chunks_count',
        'response_time_ms',
        'tokens_used',
        'user_rating',
        'created_at',
        'response_preview'
    )
    
    fieldsets = (
        ('Question', {
            'fields': ('user', 'query_text', 'created_at')
        }),
        ('Réponse', {
            'fields': ('response_preview',)
        }),
        ('Documents consultés', {
            'fields': ('source_documents',)
        }),
        ('Métriques', {
            'fields': (
                'retrieved_chunks_count',
                'response_time_ms',
                'tokens_used',
                'user_rating'
            )
        })
    )
    
    filter_horizontal = ('source_documents',)
    
    def query_preview(self, obj):
        """Aperçu de la question."""
        preview = obj.query_text[:60] + '...' if len(obj.query_text) > 60 else obj.query_text
        return format_html(
            '<div style="max-width: 300px; font-weight: bold;" title="{}">{}</div>',
            obj.query_text,
            preview
        )
    query_preview.short_description = 'Question'
    
    def documents_count(self, obj):
        """Nombre de documents consultés."""
        count = obj.source_documents.count()
        return format_html(
            '<span style="color: #3498db; font-weight: bold;">{} doc(s)</span>',
            count
        )
    documents_count.short_description = 'Documents'
    
    def chunks_count_badge(self, obj):
        """Badge pour le nombre de chunks."""
        return format_html(
            '<span style="background-color: #3498db; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 0.85em;">{} chunks</span>',
            obj.retrieved_chunks_count
        )
    chunks_count_badge.short_description = 'Chunks récupérés'
    chunks_count_badge.admin_order_field = 'retrieved_chunks_count'
    
    def response_time_badge(self, obj):
        """Badge pour le temps de réponse."""
        time_sec = obj.response_time_ms / 1000
        color = '#2ecc71' if time_sec < 2 else '#f39c12' if time_sec < 5 else '#e74c3c'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 0.85em;">{:.2f}s</span>',
            color,
            time_sec
        )
    response_time_badge.short_description = 'Temps de réponse'
    response_time_badge.admin_order_field = 'response_time_ms'
    
    def tokens_badge(self, obj):
        """Badge pour les tokens utilisés."""
        return format_html(
            '<span style="background-color: #9b59b6; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 0.85em;">{} tokens</span>',
            obj.tokens_used
        )
    tokens_badge.short_description = 'Tokens'
    tokens_badge.admin_order_field = 'tokens_used'
    
    def rating_stars(self, obj):
        """Affiche la note en étoiles."""
        if obj.user_rating:
            stars = '⭐' * obj.user_rating + '☆' * (5 - obj.user_rating)
            return format_html('<span style="font-size: 1.2em;">{}</span>', stars)
        return format_html('<span style="color: #95a5a6;">Non noté</span>')
    rating_stars.short_description = 'Note'
    rating_stars.admin_order_field = 'user_rating'
    
    def created_at_formatted(self, obj):
        """Date de création formatée."""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Date'
    created_at_formatted.admin_order_field = 'created_at'
    
    def response_preview(self, obj):
        """Aperçu de la réponse."""
        if obj.response_text:
            return format_html(
                '<div style="background-color: #ecf0f1; padding: 15px; border-radius: 5px; '
                'max-height: 300px; overflow-y: auto; white-space: pre-wrap;">{}</div>',
                obj.response_text
            )
        return '-'
    response_preview.short_description = 'Réponse complète'
    
    def has_add_permission(self, request):
        """Empêche l'ajout manuel de logs."""
        return False
