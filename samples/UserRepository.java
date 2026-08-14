package com.demo.repo;

import javax.persistence.Entity;
import javax.persistence.Id;

@Entity
public class UserRepository {

    @Id
    private Long id;

    public Long getId() {
        return id;
    }
}
