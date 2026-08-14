package com.demo.controller;

import javax.servlet.http.HttpServletRequest;
import javax.annotation.Resource;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @Resource
    private UserService userService;

    @GetMapping("/hello")
    public String hello(HttpServletRequest req) {
        return "hello";
    }
}
