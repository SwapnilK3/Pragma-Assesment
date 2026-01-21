"""
Serializers for Products app models.
"""
from rest_framework import serializers
from django.db import transaction

from core.models import MediaFile
from core import MediaType, MediaAccess
from products.models import Category, SKU, Product, ProductVariant, ProductMedia, VariantMedia


class CategorySerializer(serializers.ModelSerializer):
    """Read-only serializer for Category (used in product creation dropdown)."""

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'is_active']
        read_only_fields = ['id', 'name', 'parent', 'is_active']


class SKUSerializer(serializers.ModelSerializer):
    """Read-only serializer for SKU (used in variant creation dropdown)."""

    class Meta:
        model = SKU
        fields = ['id', 'short_name', 'description', 'quantity', 'unit']
        read_only_fields = ['id', 'short_name', 'description', 'quantity', 'unit']


class MediaFileSerializer(serializers.ModelSerializer):
    """Serializer for MediaFile (nested in product/variant)."""

    class Meta:
        model = MediaFile
        fields = ['id', 'media_type', 'extension', 'url', 'access']
        read_only_fields = ['id']


class ProductVariantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ProductVariant listing."""
    sku_name = serializers.CharField(source='product_sku.short_name', read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'price', 'sku_name', 'is_active']


class ProductVariantDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ProductVariant with media."""
    sku_name = serializers.CharField(source='product_sku.short_name', read_only=True)
    media = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'product', 'product_sku', 'sku_name', 'price',
            'media', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_media(self, obj):
        variant_media = VariantMedia.objects.filter(variant=obj).select_related('media')
        return MediaFileSerializer([vm.media for vm in variant_media], many=True).data


class ProductVariantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ProductVariant with nested media upload."""
    media_urls = serializers.ListField(
        child=serializers.URLField(),
        write_only=True,
        required=False,
        help_text="List of media URLs to attach to this variant"
    )

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'product', 'product_sku', 'price',
            'media_urls', 'is_active'
        ]
        read_only_fields = ['id']

    @transaction.atomic
    def create(self, validated_data):
        media_urls = validated_data.pop('media_urls', [])
        variant = ProductVariant.objects.create(**validated_data)

        # Create MediaFile and VariantMedia for each URL
        for url in media_urls:
            extension = url.split('.')[-1] if '.' in url else None
            media_file = MediaFile.objects.create(
                url=url,
                extension=extension,
                media_type=MediaType.IMAGE,
                access=MediaAccess.PUBLIC
            )
            VariantMedia.objects.create(variant=variant, media=media_file)

        return variant

    @transaction.atomic
    def update(self, instance, validated_data):
        media_urls = validated_data.pop('media_urls', None)

        # Update variant fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If media_urls provided, replace existing media
        if media_urls is not None:
            # Remove existing variant media
            VariantMedia.objects.filter(variant=instance).delete()

            # Create new media
            for url in media_urls:
                extension = url.split('.')[-1] if '.' in url else None
                media_file = MediaFile.objects.create(
                    url=url,
                    extension=extension,
                    media_type=MediaType.IMAGE,
                    access=MediaAccess.PUBLIC
                )
                VariantMedia.objects.create(variant=instance, media=media_file)

        return instance


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Product listing."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    variants_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'category_name', 'rating', 'variants_count', 'is_active']

    def get_variants_count(self, obj):
        return obj.variants.filter(is_active=True).count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Product with variants and media."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    variants = ProductVariantListSerializer(many=True, read_only=True)
    media = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'description_plaintext',
            'category', 'category_name', 'default_variant', 'rating',
            'variants', 'media', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_media(self, obj):
        product_media = ProductMedia.objects.filter(product=obj).select_related('media')
        return MediaFileSerializer([pm.media for pm in product_media], many=True).data


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Product with nested media and variants."""
    media_urls = serializers.ListField(
        child=serializers.URLField(),
        write_only=True,
        required=False,
        help_text="List of media URLs to attach to this product"
    )
    variants_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of variant data to create with the product"
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'description_plaintext',
            'category', 'rating', 'media_urls', 'variants_data', 'is_active'
        ]
        read_only_fields = ['id']

    @transaction.atomic
    def create(self, validated_data):
        media_urls = validated_data.pop('media_urls', [])
        variants_data = validated_data.pop('variants_data', [])

        # Create Product
        product = Product.objects.create(**validated_data)

        # Create MediaFile and ProductMedia for each URL
        for url in media_urls:
            extension = url.split('.')[-1] if '.' in url else None
            media_file = MediaFile.objects.create(
                url=url,
                extension=extension,
                media_type=MediaType.IMAGE,
                access=MediaAccess.PUBLIC
            )
            ProductMedia.objects.create(product=product, media=media_file)

        # Create variants if provided
        for variant_data in variants_data:
            variant_media_urls = variant_data.pop('media_urls', [])
            sku_id = variant_data.pop('product_sku', None)

            variant = ProductVariant.objects.create(
                product=product,
                product_sku_id=sku_id,
                **variant_data
            )

            # Create variant media
            for url in variant_media_urls:
                extension = url.split('.')[-1] if '.' in url else None
                media_file = MediaFile.objects.create(
                    url=url,
                    extension=extension,
                    media_type=MediaType.IMAGE,
                    access=MediaAccess.PUBLIC
                )
                VariantMedia.objects.create(variant=variant, media=media_file)

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        media_urls = validated_data.pop('media_urls', None)
        validated_data.pop('variants_data', None)  # Variants updated separately

        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If media_urls provided, replace existing media
        if media_urls is not None:
            ProductMedia.objects.filter(product=instance).delete()

            for url in media_urls:
                extension = url.split('.')[-1] if '.' in url else None
                media_file = MediaFile.objects.create(
                    url=url,
                    extension=extension,
                    media_type=MediaType.IMAGE,
                    access=MediaAccess.PUBLIC
                )
                ProductMedia.objects.create(product=instance, media=media_file)

        return instance
