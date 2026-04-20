from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.domain.exceptions import InsufficientFundsError, SelfTransferError
from accounts.serializers import (
    BalanceSerializer,
    ErrorSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    TransactionSerializer,
    TransferResponseSerializer,
    TransferSerializer,
)
from accounts.service_layer import handlers
from accounts.service_layer.commands import (
    GetBalance,
    ListTransactions,
    Login,
    RegisterUser,
    Transfer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary='Register a new user',
        description=(
            'Create a new user account with email and password. '
            'Automatically provisions a bank account with a unique 10-digit '
            'account number and deposits a €10,000 welcome bonus.'
        ),
        request=RegisterSerializer,
        responses={
            201: RegisterResponseSerializer,
            400: OpenApiResponse(description='Validation error (duplicate email, invalid email, short password)'),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cmd = RegisterUser(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        result = handlers.register_user(cmd)
        return Response(result, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary='Log in and obtain an auth token',
        description=(
            'Authenticate with email and password. Returns an auth token '
            'to be used as `Authorization: Token <token>` header.'
        ),
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            401: OpenApiResponse(description='Invalid credentials'),
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cmd = Login(
            email=serializer.validated_data['email'].lower(),
            password=serializer.validated_data['password'],
        )
        result = handlers.login(cmd, request=request)
        if result is None:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(result)


class BalanceView(APIView):
    @extend_schema(
        tags=['Account'],
        summary='Get current account balance',
        description='Returns the authenticated user\'s account number and current balance.',
        responses={
            200: BalanceSerializer,
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def get(self, request):
        cmd = GetBalance(user_id=request.user.pk)
        result = handlers.get_balance(cmd)
        serializer = BalanceSerializer(result)
        return Response(serializer.data)


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer

    @extend_schema(
        tags=['Account'],
        summary='List transaction history',
        description=(
            'Returns a paginated list of all transactions for the authenticated user. '
            'Each transaction includes the amount, type (CREDIT/DEBIT), description, '
            'and timestamp. Supports optional date range filtering.'
        ),
        parameters=[
            OpenApiParameter(
                name='from',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter transactions on or after this date (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='to',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter transactions on or before this date (YYYY-MM-DD)',
                required=False,
            ),
        ],
        responses={
            200: TransactionSerializer(many=True),
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        cmd = ListTransactions(
            user_id=self.request.user.pk,
            from_date=self.request.query_params.get('from'),
            to_date=self.request.query_params.get('to'),
        )
        return handlers.list_transactions(cmd)


class TransferView(APIView):
    @extend_schema(
        tags=['Transfers'],
        summary='Transfer money to another account',
        description=(
            'Transfer funds from the authenticated user\'s account to another account. '
            'A transfer fee of 2.5%% of the amount (minimum €5) is applied and deducted '
            'from the sender. Both debit (sender) and credit (receiver) transactions '
            'are recorded with a shared reference UUID.'
        ),
        request=TransferSerializer,
        responses={
            201: TransferResponseSerializer,
            400: ErrorSerializer,
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cmd = Transfer(
            from_user_id=request.user.pk,
            to_account_number=serializer.validated_data['to_account_number'],
            amount=serializer.validated_data['amount'],
        )
        try:
            result = handlers.execute_transfer(cmd)
        except SelfTransferError as e:
            return Response(
                {'error': str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except InsufficientFundsError as e:
            return Response(
                {'error': str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = TransferResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
