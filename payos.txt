package org.example.backend.controller;

import lombok.RequiredArgsConstructor;
import org.example.backend.dto.PaymentRequestDto;
import org.example.backend.dto.PaymentResponseDto;
import org.example.backend.dto.ApiResponse;
import org.example.backend.dto.PaymentHistoryDto;
import org.example.backend.dto.AdminPaymentHistoryDto;
import org.example.backend.service.PaymentService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import jakarta.servlet.http.HttpServletRequest;
import org.example.backend.repository.UserRepository;
import org.example.backend.repository.PaymentRepository;
import org.example.backend.repository.BlogPostRepository;
import org.example.backend.entity.Payment;
import org.example.backend.entity.User;
import org.example.backend.entity.BlogPost;
import org.example.backend.exception.ErrorCode;
import org.example.backend.exception.PaymentException;
import org.example.backend.service.impl.PaymentServiceImpl;
import vn.payos.PayOS;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.HashMap;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/payment")
@RequiredArgsConstructor
public class PaymentController {
    private final PaymentService paymentService;
    private final PaymentServiceImpl paymentServiceImpl;
    private final UserRepository userRepository;
    private final PaymentRepository paymentRepository;
    private final BlogPostRepository blogPostRepository;

    @Value("${payos.client-id}")
    private String clientId;
    
    @Value("${payos.api-key}")
    private String apiKey;
    
    @Value("${payos.checksum-key}")
    private String checksumKey;

    @PostMapping("/create")
    public ResponseEntity<ApiResponse<PaymentResponseDto>> createPayment(HttpServletRequest request, @RequestBody PaymentRequestDto requestDto) {
        String userEmail = (String) request.getAttribute("userEmail");
        if (userEmail == null) {
            ApiResponse<PaymentResponseDto> errorResponse = new ApiResponse<>();
            errorResponse.setCode(401);
            errorResponse.setMessage("Unauthorized");
            errorResponse.setResult(null);
            return ResponseEntity.status(401).body(errorResponse);
        }
        userRepository.findByEmail(userEmail).ifPresent(user -> requestDto.setUserId(user.getId().longValue()));
        PaymentResponseDto response = paymentService.createPayment(requestDto);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/webhook")
    public ResponseEntity<ApiResponse<String>> handleWebhook(@RequestBody Map<String, Object> payload, @RequestHeader(value = "x-client-id", required = false) String clientId) {
        try {
            System.out.println("Webhook received with payload: " + payload);
            
            if (payload == null) {
                System.out.println("Webhook payload is null");
                ApiResponse<String> errorResponse = new ApiResponse<>();
                errorResponse.setCode(400);
                errorResponse.setMessage("Webhook payload is null");
                return ResponseEntity.ok(errorResponse);
            }
            
            paymentService.handleWebhook(payload);
            
            System.out.println("Webhook processed successfully");
            return ResponseEntity.ok(ApiResponse.success("Webhook processed successfully"));
        } catch (Exception e) {
            e.printStackTrace();
            System.err.println("Error processing webhook: " + e.getMessage());
            
            ApiResponse<String> errorResponse = new ApiResponse<>();
            errorResponse.setCode(500);
            errorResponse.setMessage("Error processing webhook: " + e.getMessage());
            return ResponseEntity.ok(errorResponse);
        }
    }
    
    @GetMapping("/status/{orderId}")
    public ResponseEntity<ApiResponse<PaymentResponseDto>> getPaymentStatus(@PathVariable String orderId) {
        Optional<Payment> paymentOpt = paymentRepository.findByPayosOrderId(orderId);
        
        if (!paymentOpt.isPresent()) {
            ApiResponse<PaymentResponseDto> errorResponse = new ApiResponse<>();
            errorResponse.setCode(404);
            errorResponse.setMessage("Payment not found");
            errorResponse.setResult(null);
            return ResponseEntity.status(404).body(errorResponse);
        }
        
        Payment payment = paymentOpt.get();
        PaymentResponseDto responseDto = new PaymentResponseDto(
            payment.getPayosCheckoutUrl(),
            payment.getStatus(),
            payment.getType(),
            payment.getDuration()
        );
        
        return ResponseEntity.ok(ApiResponse.success(responseDto));
    }
    
    @GetMapping("/check-status/{orderCode}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> checkPayOSStatus(@PathVariable String orderCode) {
        try {
            Map<String, Object> statusData = paymentServiceImpl.checkPaymentStatus(orderCode);
            return ResponseEntity.ok(ApiResponse.success(statusData));
        } catch (Exception e) {
            ApiResponse<Map<String, Object>> errorResponse = new ApiResponse<>();
            errorResponse.setCode(500);
            errorResponse.setMessage("Error checking payment status: " + e.getMessage());
            errorResponse.setResult(null);
            return ResponseEntity.status(500).body(errorResponse);
        }
    }
    
    @PostMapping("/create-manual")
    public ResponseEntity<ApiResponse<PaymentResponseDto>> createManualPayment(
            HttpServletRequest request, 
            @RequestBody PaymentRequestDto requestDto) {
        
        String userEmail = (String) request.getAttribute("userEmail");
        
        String transactionId = UUID.randomUUID().toString();
        
        Payment payment = Payment.builder()
                .amount(requestDto.getAmount())
                .description(requestDto.getDescription())
                .status("PENDING")
                .payosOrderId(transactionId)
                .payosCheckoutUrl("/payment-mock?id=" + transactionId)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .type(requestDto.getType())
                .duration(requestDto.getDuration())
                .build();
        
        if (userEmail != null) {
            userRepository.findByEmail(userEmail).ifPresent(user -> {
                payment.setUser(user);
                requestDto.setUserId(user.getId().longValue());
            });
        }
        
        if (requestDto.getPostId() != null) {
            blogPostRepository.findById(requestDto.getPostId().intValue())
                    .ifPresent(payment::setPost);
        }
        
        paymentRepository.save(payment);
        
        String simulatedPaymentUrl = "/payment-mock?id=" + transactionId;
        
        return ResponseEntity.ok(ApiResponse.success(
                new PaymentResponseDto(simulatedPaymentUrl, "PENDING", 
                        requestDto.getType(), requestDto.getDuration())
        ));
    }

    @PostMapping("/complete-manual/{transactionId}")
    public ResponseEntity<ApiResponse<String>> completeManualPayment(
            @PathVariable String transactionId) {
        
        Payment payment = paymentRepository.findByPayosOrderId(transactionId)
                .orElseThrow(() -> new PaymentException(
                        ErrorCode.RESOURCE_NOT_FOUND, "Không tìm thấy giao dịch"
                ));
        
        payment.setStatus("SUCCESS");
        payment.setUpdatedAt(LocalDateTime.now());
        paymentRepository.save(payment);
        
        if ("VIP".equalsIgnoreCase(payment.getType()) && payment.getUser() != null) {
            User user = payment.getUser();
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime vipExpire = user.getVipExpireAt() != null && 
                    user.getVipExpireAt().isAfter(now) ? 
                    user.getVipExpireAt() : now;
            
            user.setVipExpireAt(vipExpire.plusMonths(payment.getDuration()));
            userRepository.save(user);
        } else if ("AD".equalsIgnoreCase(payment.getType()) && payment.getPost() != null) {
            BlogPost post = payment.getPost();
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime adExpire = post.getAdExpireAt() != null && 
                    post.getAdExpireAt().isAfter(now) ? 
                    post.getAdExpireAt() : now;
            
            post.setAdExpireAt(adExpire.plusMonths(payment.getDuration()));
            blogPostRepository.save(post);
        }
        
        return ResponseEntity.ok(ApiResponse.success("Thanh toán thành công"));
    }

    @PostMapping("/register-webhook")
    public ResponseEntity<ApiResponse<Map<String, String>>> registerWebhook(
            @RequestBody Map<String, String> request) {
        
        if (request == null || !request.containsKey("webhookUrl")) {
            return ResponseEntity.badRequest().body(
                ApiResponse.error("Missing webhookUrl parameter")
            );
        }
        
        String webhookUrl = request.get("webhookUrl");
        
        try {
            Map<String, String> result = new HashMap<>();
            result.put("status", "success");
            result.put("webhookUrl", webhookUrl);
            
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("Failed to register webhook: " + e.getMessage()));
        }
    }
    
    @GetMapping("/create-wallet-payment")
    public ResponseEntity<ApiResponse<PaymentResponseDto>> createWalletPayment(
            @RequestParam(required = false) Integer userId,
            @RequestParam Long amount) {
        
        try {
            // Nếu không có userId, lấy từ token JWT hiện tại
            if (userId == null) {
                Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
                if (authentication != null) {
                    String email = authentication.getName();
                    User currentUser = userRepository.findByEmail(email).orElse(null);
                    if (currentUser != null) {
                        userId = currentUser.getId();
                    }
                }
            }
            
            if (userId == null) {
                return ResponseEntity.badRequest().body(
                    ApiResponse.error("Không có thông tin người dùng")
                );
            }
            
            // Tìm thông tin người dùng
            User user = userRepository.findById(userId).orElse(null);
            if (user == null) {
                return ResponseEntity.badRequest().body(
                    ApiResponse.error("Không tìm thấy người dùng với ID: " + userId)
                );
            }
            
            System.out.println("Tạo giao dịch nạp tiền vào ví cho user: " + userId + ", số tiền: " + amount);
            
            // Chuẩn bị thông tin thanh toán
            PaymentRequestDto paymentRequest = PaymentRequestDto.builder()
                .amount(amount)
                .type("WALLET")
                .description("Nạp tiền vào ví " + amount + " VND")
                .userId(Long.valueOf(userId))
                .returnUrl("http://localhost:3000/wallet/success")
                .cancelUrl("http://localhost:3000/wallet/cancel")
                .build();
            
            // Tạo thanh toán
            PaymentResponseDto paymentResponse = paymentService.createPayment(paymentRequest);
            
            return ResponseEntity.ok(ApiResponse.success(paymentResponse));
        } catch (Exception e) {
            System.err.println("Lỗi khi tạo giao dịch nạp tiền vào ví: " + e.getMessage());
            e.printStackTrace();
            return ResponseEntity.status(500).body(
                ApiResponse.error("Lỗi khi tạo giao dịch: " + e.getMessage())
            );
        }
    }

    @GetMapping("/history")
    public ResponseEntity<ApiResponse<List<PaymentHistoryDto>>> getPaymentHistory() {
        try {
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (authentication == null) {
                return ResponseEntity.status(401).body(
                    ApiResponse.error("Unauthorized")
                );
            }
            
            String email = authentication.getName();
            User currentUser = userRepository.findByEmail(email)
                .orElseThrow(() -> new RuntimeException("User not found"));
            
            List<Payment> payments = paymentRepository.findByUserOrderByCreatedAtDesc(currentUser);
            List<PaymentHistoryDto> paymentDtos = payments.stream()
                .map(PaymentHistoryDto::fromEntity)
                .collect(Collectors.toList());
            
            return ResponseEntity.ok(ApiResponse.success(paymentDtos));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                ApiResponse.error("Error getting payment history: " + e.getMessage())
            );
        }
    }

    @GetMapping("/history/all")
    public ResponseEntity<ApiResponse<List<AdminPaymentHistoryDto>>> getAllPaymentHistory() {
        try {
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (authentication == null) {
                return ResponseEntity.status(401).body(
                    ApiResponse.error("Unauthorized")
                );
            }
            
            String email = authentication.getName();
            User currentUser = userRepository.findByEmail(email)
                .orElseThrow(() -> new RuntimeException("User not found"));
                
            boolean isAdmin = currentUser.getRole() != null && 
                    "ADMIN".equalsIgnoreCase(currentUser.getRole().getRoleName());
            if (!isAdmin) {
                return ResponseEntity.status(403).body(
                    ApiResponse.error("Chỉ ADMIN mới có quyền xem tất cả lịch sử giao dịch")
                );
            }
            
            List<Payment> payments = paymentRepository.findAllByOrderByCreatedAtDesc();
            List<AdminPaymentHistoryDto> paymentDtos = payments.stream()
                .map(AdminPaymentHistoryDto::fromEntity)
                .collect(Collectors.toList());
            
            return ResponseEntity.ok(ApiResponse.success(paymentDtos));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                ApiResponse.error("Error getting all payment history: " + e.getMessage())
            );
        }
    }
} 